import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tabs,
  Tab,
  LinearProgress,
  Chip,
  Grid,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
} from '@mui/material';
import {
  Event as EventIcon,
  CalendarToday as CalendarIcon,
  Schedule as ScheduleIcon,
  Notifications as NotificationIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  AccessTime as TimeIcon,
  Today as TodayIcon,
  ViewWeek as WeekIcon,
  ViewModule as MonthIcon,
} from '@mui/icons-material';
import { apiService } from '../services/apiService';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`schedule-tabpanel-${index}`}
      aria-labelledby={`schedule-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

interface ScheduleEvent {
  id: string;
  title: string;
  description: string;
  start_time: string;
  end_time?: string;
  reminder_minutes?: number;
  priority?: 'low' | 'medium' | 'high';
  status: 'pending' | 'completed' | 'cancelled';
  created_at: string;
}

/**
 * 日程管理器组件
 * 提供事件创建、日历视图、提醒设置等功能
 */
const ScheduleManager: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(false);
  const [events, setEvents] = useState<ScheduleEvent[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<ScheduleEvent | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [viewMode, setViewMode] = useState<'day' | 'week' | 'month'>('week');

  // 表单数据
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    start_time: '',
    end_time: '',
    reminder_minutes: 15,
    repeat_type: 'none', // none, daily, weekly, monthly
    priority: 'medium', // low, medium, high
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const loadEvents = async () => {
    try {
      setLoading(true);
      const response = await apiService.getTasks('scheduler');
      // 转换任务数据为事件格式
      const eventData: ScheduleEvent[] = response.data.map((task: any) => ({
        id: task.id,
        title: task.title,
        description: task.description,
        start_time: task.parameters.start_time,
        end_time: task.parameters.end_time,
        reminder_minutes: task.parameters.reminder_minutes,
        priority: task.parameters.priority || 'medium',
        status: task.status === 'completed' ? 'completed' as const : 'pending' as const,
        created_at: task.created_at,
      }));
      setEvents(eventData);
    } catch (error) {
      console.error('加载日程失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
    
    // 请求通知权限
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []); // 只在组件挂载时加载一次

  useEffect(() => {
    // 将showNotification函数移到useEffect内部
    const showNotification = (event: ScheduleEvent) => {
      if ('Notification' in window && Notification.permission === 'granted') {
        const notification = new Notification(`日程提醒: ${event.title}`, {
          body: `${event.description}\n开始时间: ${formatDateTime(event.start_time)}`,
          icon: '/favicon.ico',
          tag: `schedule-${event.id}` // 防止重复通知
        });
        
        notification.onclick = () => {
          window.focus();
          notification.close();
        };
        
        // 5秒后自动关闭
        setTimeout(() => notification.close(), 5000);
      }
    };

    // 设置定期检查提醒
    const checkReminders = () => {
      const now = new Date();
      events.forEach(event => {
        if (event.status === 'pending' && event.reminder_minutes) {
          const eventTime = new Date(event.start_time);
          const reminderTime = new Date(eventTime.getTime() - event.reminder_minutes * 60000);
          
          if (now >= reminderTime && now < eventTime) {
            showNotification(event);
          }
        }
      });
    };
    
    // 设置60秒定时刷新和提醒检查
    const refreshInterval = setInterval(() => {
      loadEvents(); // 60秒刷新一次数据
    }, 60000);
    
    const reminderInterval = setInterval(checkReminders, 60000); // 每分钟检查提醒
    
    return () => {
      clearInterval(refreshInterval);
      clearInterval(reminderInterval);
    };
  }, [events]);

  const handleCreateEvent = async () => {
    try {
      setLoading(true);

      const taskData = {
        title: formData.title,
        description: formData.description,
        tool_type: 'scheduler',
        parameters: {
          title: formData.title,
          description: formData.description,
          start_time: formData.start_time,
          end_time: formData.end_time,
          reminder_minutes: formData.reminder_minutes,
          repeat_type: formData.repeat_type,
          priority: formData.priority
        }
      };

      const response = await apiService.createTask(taskData);
      
      // 轮询任务状态
      const taskId = response.data.id;
      const maxWaitTime = 30000; // 30秒
      const checkInterval = 1000; // 1秒
      let waited = 0;
      
      const checkStatus = async () => {
        try {
          const statusResponse = await apiService.getTask(taskId);
          const task = statusResponse.data;
          
          if (task.status === 'completed') {
      // 重新加载事件列表
      await loadEvents();
      
      // 重置表单
      setFormData({
        title: '',
        description: '',
        start_time: '',
        end_time: '',
        reminder_minutes: 15,
        repeat_type: 'none',
        priority: 'medium',
      });
      
      setDialogOpen(false);
            
            // 设置浏览器提醒
            if ('Notification' in window) {
              Notification.requestPermission();
            }
            
            return;
          } else if (task.status === 'failed') {
            throw new Error(task.error_message || '任务失败');
          }
          
          // 继续等待
          waited += checkInterval;
          if (waited < maxWaitTime) {
            setTimeout(checkStatus, checkInterval);
          } else {
            throw new Error('任务超时');
          }
        } catch (error) {
          console.error('检查任务状态失败:', error);
        }
      };
      
      setTimeout(checkStatus, checkInterval);
      
    } catch (error) {
      console.error('创建日程失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEditEvent = (event: ScheduleEvent) => {
    setSelectedEvent(event);
    setFormData({
      title: event.title,
      description: event.description,
      start_time: event.start_time,
      end_time: event.end_time || '',
      reminder_minutes: event.reminder_minutes || 15,
      repeat_type: 'none',
      priority: 'medium',
    });
    setDialogOpen(true);
  };

  const handleDeleteEvent = async (eventId: string) => {
    if (window.confirm('确定要删除这个日程吗？')) {
      try {
        await apiService.deleteTask(eventId);
        await loadEvents();
      } catch (error) {
        console.error('删除日程失败:', error);
      }
    }
  };

  const formatDateTime = (dateTimeStr: string) => {
    if (!dateTimeStr) return '';
    const date = new Date(dateTimeStr);
    return date.toLocaleString('zh-CN');
  };

  const getEventsByDate = (date: Date) => {
    const dateStr = date.toISOString().split('T')[0];
    return events.filter(event => 
      event.start_time.startsWith(dateStr)
    );
  };

  const getTodayEvents = () => {
    const today = new Date();
    return getEventsByDate(today);
  };

  const getUpcomingEvents = () => {
    const now = new Date();
    const nextWeek = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
    
    return events.filter(event => {
      const eventDate = new Date(event.start_time);
      return eventDate >= now && eventDate <= nextWeek;
    }).sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());
  };

  const generateCalendarDays = () => {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth();
    
    // 获取月份第一天
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    
    // 获取第一天是星期几
    const firstDayOfWeek = firstDay.getDay();
    
    // 生成日历天数组
    const days = [];
    
    // 添加上个月的天数来填充第一周
    const prevMonth = new Date(year, month - 1, 0);
    for (let i = firstDayOfWeek - 1; i >= 0; i--) {
      const date = prevMonth.getDate() - i;
      days.push({
        date,
        isCurrentMonth: false,
        isToday: false,
        events: []
      });
    }
    
    // 添加当月的天数
    for (let date = 1; date <= lastDay.getDate(); date++) {
      const isToday = now.getDate() === date && 
                     now.getMonth() === month && 
                     now.getFullYear() === year;
      
      // 获取这一天的事件
      const dayEvents = events.filter(event => {
        const eventDate = new Date(event.start_time);
        return eventDate.getDate() === date && 
               eventDate.getMonth() === month && 
               eventDate.getFullYear() === year;
      });
      
      days.push({
        date,
        isCurrentMonth: true,
        isToday,
        events: dayEvents
      });
    }
    
    // 添加下个月的天数来填充最后一周
    const remainingDays = 42 - days.length; // 6周 * 7天
    for (let date = 1; date <= remainingDays; date++) {
      days.push({
        date,
        isCurrentMonth: false,
        isToday: false,
        events: []
      });
    }
    
    return days;
  };

  const resetForm = () => {
    setFormData({
      title: '',
      description: '',
      start_time: '',
      end_time: '',
      reminder_minutes: 15,
      repeat_type: 'none',
      priority: 'medium',
    });
    setSelectedEvent(null);
    setDialogOpen(false);
  };

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 600 }}>
          📅 日程管理
        </Typography>
        <Typography variant="body1" color="text.secondary">
          管理您的日程安排，设置提醒和重复事件
        </Typography>
      </Box>

      {/* 快速操作栏 */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setDialogOpen(true)}
        >
          新建日程
        </Button>
        <Button
          variant="outlined"
          startIcon={<TodayIcon />}
          onClick={() => setViewMode('day')}
          color={viewMode === 'day' ? 'primary' : 'inherit'}
        >
          日视图
        </Button>
        <Button
          variant="outlined"
          startIcon={<WeekIcon />}
          onClick={() => setViewMode('week')}
          color={viewMode === 'week' ? 'primary' : 'inherit'}
        >
          周视图
        </Button>
        <Button
          variant="outlined"
          startIcon={<MonthIcon />}
          onClick={() => setViewMode('month')}
          color={viewMode === 'month' ? 'primary' : 'inherit'}
        >
          月视图
        </Button>
      </Box>

      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab icon={<TodayIcon />} label="今日日程" />
            <Tab icon={<ScheduleIcon />} label="即将到来" />
            <Tab icon={<CalendarIcon />} label="所有日程" />
            <Tab icon={<CalendarIcon />} label="日历视图" />
          </Tabs>
        </Box>

        {/* 今日日程 */}
        <TabPanel value={tabValue} index={0}>
          <CardContent>
            {loading ? (
              <LinearProgress />
            ) : (
              <Box>
                <Typography variant="h6" gutterBottom>
                  今天的日程安排
                </Typography>
                {getTodayEvents().length > 0 ? (
                  <List>
                    {getTodayEvents().map((event) => (
                      <ListItem
                        key={event.id}
                        sx={{
                          border: 1,
                          borderColor: 'divider',
                          borderRadius: 1,
                          mb: 1,
                        }}
                      >
                        <ListItemIcon>
                          <EventIcon color={event.status === 'completed' ? 'success' : 'primary'} />
                        </ListItemIcon>
                        <ListItemText
                          primary={event.title}
                          secondary={
                            <Box>
                              <Typography variant="body2" color="text.secondary">
                                {event.description}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                <TimeIcon sx={{ fontSize: 14, mr: 0.5 }} />
                                {formatDateTime(event.start_time)}
                                {event.end_time && ` - ${formatDateTime(event.end_time)}`}
                              </Typography>
                            </Box>
                          }
                        />
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <IconButton
                            size="small"
                            onClick={() => handleEditEvent(event)}
                          >
                            <EditIcon />
                          </IconButton>
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleDeleteEvent(event.id)}
                          >
                            <DeleteIcon />
                          </IconButton>
                        </Box>
                      </ListItem>
                    ))}
                  </List>
                ) : (
                  <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
                    今天没有安排的日程
                  </Typography>
                )}
              </Box>
            )}
          </CardContent>
        </TabPanel>

        {/* 即将到来 */}
        <TabPanel value={tabValue} index={1}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              未来一周的日程
            </Typography>
            {getUpcomingEvents().length > 0 ? (
              <List>
                {getUpcomingEvents().map((event) => (
                  <ListItem
                    key={event.id}
                    sx={{
                      border: 1,
                      borderColor: 'divider',
                      borderRadius: 1,
                      mb: 1,
                    }}
                  >
                    <ListItemIcon>
                      <EventIcon color="primary" />
                    </ListItemIcon>
                    <ListItemText
                      primary={event.title}
                      secondary={
                        <Box>
                          <Typography variant="body2" color="text.secondary">
                            {event.description}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            <TimeIcon sx={{ fontSize: 14, mr: 0.5 }} />
                            {formatDateTime(event.start_time)}
                          </Typography>
                          {event.reminder_minutes && (
                            <Chip
                              size="small"
                              icon={<NotificationIcon />}
                              label={`提前${event.reminder_minutes}分钟提醒`}
                              sx={{ ml: 1 }}
                            />
                          )}
                        </Box>
                      }
                    />
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <IconButton
                        size="small"
                        onClick={() => handleEditEvent(event)}
                      >
                        <EditIcon />
                      </IconButton>
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleDeleteEvent(event.id)}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Box>
                  </ListItem>
                ))}
              </List>
            ) : (
              <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
                未来一周没有安排的日程
              </Typography>
            )}
          </CardContent>
        </TabPanel>

        {/* 所有日程 */}
        <TabPanel value={tabValue} index={2}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              所有日程安排
            </Typography>
            {events.length > 0 ? (
              <List>
                {events.map((event) => (
                  <ListItem
                    key={event.id}
                    sx={{
                      border: 1,
                      borderColor: 'divider',
                      borderRadius: 1,
                      mb: 1,
                    }}
                  >
                    <ListItemIcon>
                      <EventIcon color={event.status === 'completed' ? 'success' : 'primary'} />
                    </ListItemIcon>
                    <ListItemText
                      primary={event.title}
                      secondary={
                        <Box>
                          <Typography variant="body2" color="text.secondary">
                            {event.description}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            <TimeIcon sx={{ fontSize: 14, mr: 0.5 }} />
                            {formatDateTime(event.start_time)}
                          </Typography>
                          <Chip
                            size="small"
                            label={event.status === 'completed' ? '已完成' : '待进行'}
                            color={event.status === 'completed' ? 'success' : 'default'}
                            sx={{ ml: 1 }}
                          />
                        </Box>
                      }
                    />
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <IconButton
                        size="small"
                        onClick={() => handleEditEvent(event)}
                      >
                        <EditIcon />
                      </IconButton>
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleDeleteEvent(event.id)}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Box>
                  </ListItem>
                ))}
              </List>
            ) : (
              <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
                暂无日程安排
              </Typography>
            )}
          </CardContent>
        </TabPanel>

        {/* 日历视图 */}
        <TabPanel value={tabValue} index={3}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              日历视图 - {viewMode === 'day' ? '日视图' : viewMode === 'week' ? '周视图' : '月视图'}
            </Typography>
            
            {viewMode === 'day' && (
              <Box>
                <Typography variant="h6" gutterBottom>
                  {new Date().toLocaleDateString('zh-CN', { 
                    year: 'numeric', 
                    month: 'long', 
                    day: 'numeric',
                    weekday: 'long'
                  })}
                </Typography>
                <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 2 }}>
                  {getTodayEvents().length > 0 ? (
                    <List>
                      {getTodayEvents().map((event) => (
                        <ListItem
                          key={event.id}
                          sx={{
                            border: 1,
                            borderColor: 'divider',
                            borderRadius: 1,
                            mb: 1,
                          }}
                        >
                          <ListItemIcon>
                            <EventIcon color={event.status === 'completed' ? 'success' : 'primary'} />
                          </ListItemIcon>
                          <ListItemText
                            primary={event.title}
                            secondary={
                              <Box>
                                <Typography variant="body2" color="text.secondary">
                                  {event.description}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  <TimeIcon sx={{ fontSize: 14, mr: 0.5 }} />
                                  {formatDateTime(event.start_time)}
                                  {event.end_time && ` - ${formatDateTime(event.end_time)}`}
                                </Typography>
                              </Box>
                            }
                          />
                        </ListItem>
                      ))}
                    </List>
                  ) : (
                    <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
                      今天没有安排的日程
                    </Typography>
                  )}
                </Box>
              </Box>
            )}

            {viewMode === 'week' && (
              <Box>
                <Typography variant="h6" gutterBottom>
                  本周日程
                </Typography>
                <Box sx={{ 
                  display: 'grid', 
                  gridTemplateColumns: 'repeat(7, 1fr)', 
                  gap: 1, 
                  mb: 2 
                }}>
                  {['周日', '周一', '周二', '周三', '周四', '周五', '周六'].map(day => (
                    <Typography 
                      key={day} 
                      variant="subtitle2" 
                      sx={{ 
                        textAlign: 'center', 
                        fontWeight: 'bold',
                        p: 1,
                        bgcolor: 'grey.100',
                        borderRadius: 1
                      }}
                    >
                      {day}
                    </Typography>
                  ))}
                </Box>
                <Box sx={{ 
                  display: 'grid', 
                  gridTemplateColumns: 'repeat(7, 1fr)', 
                  gap: 1,
                  minHeight: 200
                }}>
                  {(() => {
                    const today = new Date();
                    const startOfWeek = new Date(today);
                    startOfWeek.setDate(today.getDate() - today.getDay());
                    
                    return Array.from({ length: 7 }, (_, i) => {
                      const date = new Date(startOfWeek);
                      date.setDate(startOfWeek.getDate() + i);
                      const dayEvents = getEventsByDate(date);
                      
                      return (
                        <Box
                          key={i}
                          sx={{
                            border: 1,
                            borderColor: 'divider',
                            borderRadius: 1,
                            p: 1,
                            minHeight: 120,
                            bgcolor: 'background.paper'
                          }}
                        >
                          <Typography 
                            variant="caption" 
                            sx={{ 
                              color: date.toDateString() === today.toDateString() ? 'primary.main' : 'text.primary',
                              fontWeight: date.toDateString() === today.toDateString() ? 'bold' : 'normal'
                            }}
                          >
                            {date.getDate()}
                          </Typography>
                          {dayEvents.map((event, eventIndex) => (
                            <Box
                              key={eventIndex}
                              sx={{
                                mt: 0.5,
                                p: 0.5,
                                bgcolor: event.priority === 'high' ? 'error.light' : 
                                       event.priority === 'medium' ? 'warning.light' : 'success.light',
                                borderRadius: 0.5,
                                fontSize: '0.7rem',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap'
                              }}
                              title={event.title}
                            >
                              {event.title}
                            </Box>
                          ))}
                        </Box>
                      );
                    });
                  })()}
                </Box>
              </Box>
            )}

            {viewMode === 'month' && (
              <Box>
                <Typography variant="h6" gutterBottom>
                  {new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long' })}
                </Typography>
                <Box sx={{ 
                  display: 'grid', 
                  gridTemplateColumns: 'repeat(7, 1fr)', 
                  gap: 1, 
                  mb: 2 
                }}>
                  {['周日', '周一', '周二', '周三', '周四', '周五', '周六'].map(day => (
                    <Typography 
                      key={day} 
                      variant="subtitle2" 
                      sx={{ 
                        textAlign: 'center', 
                        fontWeight: 'bold',
                        p: 1,
                        bgcolor: 'grey.100',
                        borderRadius: 1
                      }}
                    >
                      {day}
                    </Typography>
                  ))}
                </Box>
                <Box sx={{ 
                  display: 'grid', 
                  gridTemplateColumns: 'repeat(7, 1fr)', 
                  gap: 1,
                  minHeight: 400
                }}>
                  {generateCalendarDays().map((day, index) => (
                    <Box
                      key={index}
                      sx={{
                        border: 1,
                        borderColor: 'divider',
                        borderRadius: 1,
                        p: 1,
                        minHeight: 80,
                        bgcolor: day.isCurrentMonth ? 'background.paper' : 'grey.50',
                        position: 'relative'
                      }}
                    >
                      <Typography 
                        variant="caption" 
                        sx={{ 
                          color: day.isToday ? 'primary.main' : 'text.primary',
                          fontWeight: day.isToday ? 'bold' : 'normal'
                        }}
                      >
                        {day.date}
                      </Typography>
                      {day.events.map((event, eventIndex) => (
                        <Box
                          key={eventIndex}
                          sx={{
                            mt: 0.5,
                            p: 0.5,
                            bgcolor: event.priority === 'high' ? 'error.light' : 
                                   event.priority === 'medium' ? 'warning.light' : 'success.light',
                            borderRadius: 0.5,
                            fontSize: '0.7rem',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap'
                          }}
                          title={event.title}
                        >
                          {event.title}
                        </Box>
                      ))}
                    </Box>
                  ))}
                </Box>
              </Box>
            )}
          </CardContent>
        </TabPanel>
      </Card>

      {/* 创建/编辑日程对话框 */}
      <Dialog open={dialogOpen} onClose={resetForm} maxWidth="md" fullWidth>
        <DialogTitle>
          {selectedEvent ? '编辑日程' : '新建日程'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              fullWidth
              label="日程标题"
              value={formData.title}
              onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
              required
            />
            
            <TextField
              fullWidth
              label="日程描述"
              multiline
              rows={3}
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
            />

            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="开始时间"
                  type="datetime-local"
                  value={formData.start_time}
                  onChange={(e) => setFormData(prev => ({ ...prev, start_time: e.target.value }))}
                  InputLabelProps={{ shrink: true }}
                  required
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="结束时间"
                  type="datetime-local"
                  value={formData.end_time}
                  onChange={(e) => setFormData(prev => ({ ...prev, end_time: e.target.value }))}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
            </Grid>

            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>提醒时间</InputLabel>
                  <Select
                    value={formData.reminder_minutes}
                    label="提醒时间"
                    onChange={(e) => setFormData(prev => ({ ...prev, reminder_minutes: Number(e.target.value) }))}
                  >
                    <MenuItem value={0}>不提醒</MenuItem>
                    <MenuItem value={5}>提前5分钟</MenuItem>
                    <MenuItem value={15}>提前15分钟</MenuItem>
                    <MenuItem value={30}>提前30分钟</MenuItem>
                    <MenuItem value={60}>提前1小时</MenuItem>
                    <MenuItem value={1440}>提前1天</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>重复类型</InputLabel>
                  <Select
                    value={formData.repeat_type}
                    label="重复类型"
                    onChange={(e) => setFormData(prev => ({ ...prev, repeat_type: e.target.value }))}
                  >
                    <MenuItem value="none">不重复</MenuItem>
                    <MenuItem value="daily">每天</MenuItem>
                    <MenuItem value="weekly">每周</MenuItem>
                    <MenuItem value="monthly">每月</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>

            <FormControl fullWidth>
              <InputLabel>优先级</InputLabel>
              <Select
                value={formData.priority}
                label="优先级"
                onChange={(e) => setFormData(prev => ({ ...prev, priority: e.target.value }))}
              >
                <MenuItem value="low">低</MenuItem>
                <MenuItem value="medium">中</MenuItem>
                <MenuItem value="high">高</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={resetForm}>取消</Button>
          <Button onClick={handleCreateEvent} variant="contained" disabled={loading}>
            {selectedEvent ? '更新' : '创建'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ScheduleManager; 