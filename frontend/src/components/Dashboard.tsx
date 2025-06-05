import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  LinearProgress,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Paper,
} from '@mui/material';
import {
  CheckCircle as CompletedIcon,
  Schedule as PendingIcon,
  Error as ErrorIcon,
  TrendingUp as TrendingIcon,
} from '@mui/icons-material';
import { apiService } from '../services/apiService';

/**
 * 任务统计接口
 */
interface TaskStats {
  total: number;
  completed: number;
  pending: number;
  failed: number;
}

/**
 * 最近任务接口
 */
interface RecentTask {
  id: string;
  title: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_at: string;
  tool_type: string;
}

/**
 * 仪表板组件
 * 显示应用的概览信息、任务统计和最近活动
 */
const Dashboard: React.FC = () => {
  const [taskStats, setTaskStats] = useState<TaskStats>({
    total: 0,
    completed: 0,
    pending: 0,
    failed: 0,
  });
  const [recentTasks, setRecentTasks] = useState<RecentTask[]>([]);
  const [loading, setLoading] = useState(true);

  /**
   * 加载仪表板数据
   */
  const loadDashboardData = async () => {
    try {
      setLoading(true);
      
      // 并行加载任务统计和最近任务
      const [statsResponse, tasksResponse] = await Promise.all([
        apiService.getTaskStats(),
        apiService.getRecentTasks(5),
      ]);

      setTaskStats(statsResponse.data);
      setRecentTasks(tasksResponse.data);
    } catch (error) {
      console.error('加载仪表板数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // 初始加载
    loadDashboardData();

    // 设置1分钟自动刷新
    const interval = setInterval(() => {
      console.log('仪表板自动刷新...');
      loadDashboardData();
    }, 60000); // 60秒 = 1分钟

    // 页面可见性变化时刷新
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        console.log('页面重新可见，刷新仪表板...');
        loadDashboardData();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    // 清理函数
    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  /**
   * 获取任务状态图标
   */
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CompletedIcon color="success" />;
      case 'pending':
      case 'running':
        return <PendingIcon color="warning" />;
      case 'failed':
        return <ErrorIcon color="error" />;
      default:
        return <PendingIcon />;
    }
  };

  /**
   * 获取任务状态颜色
   */
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'pending':
      case 'running':
        return 'warning';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  /**
   * 计算完成率
   */
  const completionRate = taskStats.total > 0 ? (taskStats.completed / taskStats.total) * 100 : 0;

  if (loading) {
    return (
      <Box sx={{ width: '100%' }}>
        <LinearProgress />
        <Typography variant="h6" sx={{ mt: 2, textAlign: 'center' }}>
          加载仪表板数据...
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 600 }}>
          📊 仪表板
        </Typography>
        <Typography variant="body1" color="text.secondary">
          欢迎使用多功能 AI 应用，这里是您的工作概览
        </Typography>
      </Box>

      {/* 统计卡片 */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
            <CardContent>
              <Typography color="inherit" gutterBottom sx={{ opacity: 0.9 }}>
                总任务数
              </Typography>
              <Typography variant="h3" component="div" sx={{ fontWeight: 700, mb: 2 }}>
                {taskStats.total}
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <TrendingIcon sx={{ mr: 1, opacity: 0.9 }} />
                <Typography variant="body2" sx={{ opacity: 0.9 }}>
                  全部任务
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)', color: 'white' }}>
            <CardContent>
              <Typography color="inherit" gutterBottom sx={{ opacity: 0.9 }}>
                已完成
              </Typography>
              <Typography variant="h3" component="div" sx={{ fontWeight: 700, mb: 2 }}>
                {taskStats.completed}
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <CompletedIcon sx={{ mr: 1, opacity: 0.9 }} />
                <Typography variant="body2" sx={{ opacity: 0.9 }}>
                  完成率 {completionRate.toFixed(1)}%
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', color: 'white' }}>
            <CardContent>
              <Typography color="inherit" gutterBottom sx={{ opacity: 0.9 }}>
                进行中
              </Typography>
              <Typography variant="h3" component="div" sx={{ fontWeight: 700, mb: 2 }}>
                {taskStats.pending}
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <PendingIcon sx={{ mr: 1, opacity: 0.9 }} />
                <Typography variant="body2" sx={{ opacity: 0.9 }}>
                  待处理任务
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #fc466b 0%, #3f5efb 100%)', color: 'white' }}>
            <CardContent>
              <Typography color="inherit" gutterBottom sx={{ opacity: 0.9 }}>
                失败
              </Typography>
              <Typography variant="h3" component="div" sx={{ fontWeight: 700, mb: 2 }}>
                {taskStats.failed}
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <ErrorIcon sx={{ mr: 1, opacity: 0.9 }} />
                <Typography variant="body2" sx={{ opacity: 0.9 }}>
                  需要重试
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* 完成率进度条 */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              任务完成进度
            </Typography>
            <Box sx={{ mt: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2">完成率</Typography>
                <Typography variant="body2">{completionRate.toFixed(1)}%</Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={completionRate}
                sx={{ height: 8, borderRadius: 4 }}
              />
            </Box>
          </Paper>
        </Grid>

        {/* 最近任务 */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              最近任务
            </Typography>
            {recentTasks.length > 0 ? (
              <List dense>
                {recentTasks.map((task) => (
                  <ListItem key={task.id} sx={{ px: 0 }}>
                    <ListItemIcon>
                      {getStatusIcon(task.status)}
                    </ListItemIcon>
                    <ListItemText
                      primary={task.title}
                      secondary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                          <Chip
                            label={task.tool_type}
                            size="small"
                            variant="outlined"
                          />
                          <Chip
                            label={task.status}
                            size="small"
                            color={getStatusColor(task.status) as any}
                          />
                          <Typography variant="caption" color="textSecondary">
                            {new Date(task.created_at).toLocaleString('zh-CN')}
                          </Typography>
                        </Box>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            ) : (
              <Typography color="textSecondary" sx={{ textAlign: 'center', py: 2 }}>
                暂无最近任务
              </Typography>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard; 