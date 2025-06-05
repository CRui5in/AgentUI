import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Chip,
  Grid,
  Paper,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Close as CloseIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon,
  ContentCopy as CopyIcon,
} from '@mui/icons-material';
import { Task } from '../services/apiService';
import { apiService } from '../services/apiService';

interface TaskDetailProps {
  open: boolean;
  onClose: () => void;
  taskId: string | null;
}

const TaskDetail: React.FC<TaskDetailProps> = ({ open, onClose, taskId }) => {
  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 获取任务详情
  const fetchTaskDetail = async () => {
    if (!taskId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await apiService.getTask(taskId);
      setTask(response.data);
    } catch (err: any) {
      console.error('获取任务详情失败:', err);
      setError(err.response?.data?.detail || '获取任务详情失败');
    } finally {
      setLoading(false);
    }
  };

  // 当对话框打开且有任务ID时获取详情
  useEffect(() => {
    if (open && taskId) {
      fetchTaskDetail();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, taskId]);

  // 获取状态颜色
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

  // 获取状态文本
  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
        return '已完成';
      case 'pending':
        return '等待中';
      case 'running':
        return '运行中';
      case 'failed':
        return '失败';
      default:
        return status;
    }
  };

  // 下载文件
  const handleDownload = async () => {
    if (!task?.result) return;

    try {
      let downloadUrl = '';
      let filename = '';
      
      // 根据任务类型处理不同的下载逻辑
      if (task.tool_type === 'ppt_generator' && task.result.pdf_path) {
        // PPT文件下载
        const normalizedPath = task.result.pdf_path.replace(/\\/g, '/');
        filename = normalizedPath.split('/').pop() || 'download.pdf';
        downloadUrl = `http://localhost:8002/download/${filename}`;
      } else if (task.tool_type === 'chart_generator' && (task.result.filename || task.result.image_path)) {
        // 图表文件下载
        filename = task.result.filename || task.result.image_path.split('/').pop() || 'chart.png';
        downloadUrl = `http://localhost:8003/download/${filename}`;
      } else {
        console.warn('无可下载的文件');
        return;
      }
      
      console.log('下载URL:', downloadUrl);
      console.log('文件名:', filename);
      
      // 创建临时链接下载
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error('下载失败:', err);
    }
  };

  // 复制内容到剪贴板
  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      // 可以添加成功提示
    } catch (err) {
      console.error('复制失败:', err);
    }
  };

  // 格式化时间
  const formatTime = (timeString: string) => {
    return new Date(timeString).toLocaleString('zh-CN');
  };

  // 格式化参数显示
  const formatParameters = (params: Record<string, any>) => {
    return Object.entries(params).map(([key, value]) => (
      <Box key={key} sx={{ mb: 1 }}>
        <Typography variant="body2" color="text.secondary" component="span">
          {key}:
        </Typography>
        <Typography variant="body2" component="span" sx={{ ml: 1 }}>
          {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
        </Typography>
      </Box>
    ));
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { minHeight: '60vh' }
      }}
    >
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">任务详情</Typography>
          <Box>
            <Tooltip title="刷新">
              <IconButton onClick={fetchTaskDetail} disabled={loading}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
            <IconButton onClick={onClose}>
              <CloseIcon />
            </IconButton>
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        {loading && (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
            <CircularProgress />
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {task && !loading && (
          <Grid container spacing={3}>
            {/* 基本信息 */}
            <Grid item xs={12}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  基本信息
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="body2" color="text.secondary">
                      任务ID
                    </Typography>
                    <Box display="flex" alignItems="center">
                      <Typography variant="body1" sx={{ fontFamily: 'monospace', mr: 1 }}>
                        {task.id}
                      </Typography>
                      <IconButton size="small" onClick={() => handleCopy(task.id)}>
                        <CopyIcon fontSize="small" />
                      </IconButton>
                    </Box>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="body2" color="text.secondary">
                      状态
                    </Typography>
                    <Chip
                      label={getStatusText(task.status)}
                      color={getStatusColor(task.status) as any}
                      size="small"
                      sx={{ mt: 0.5 }}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <Typography variant="body2" color="text.secondary">
                      标题
                    </Typography>
                    <Typography variant="body1">{task.title}</Typography>
                  </Grid>
                  <Grid item xs={12}>
                    <Typography variant="body2" color="text.secondary">
                      描述
                    </Typography>
                    <Typography variant="body1">{task.description || '无描述'}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="body2" color="text.secondary">
                      工具类型
                    </Typography>
                    <Typography variant="body1">{task.tool_type}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="body2" color="text.secondary">
                      创建时间
                    </Typography>
                    <Typography variant="body1">{formatTime(task.created_at)}</Typography>
                  </Grid>
                  {/* 如果有可下载的文件，显示下载按钮 */}
                  {((task.tool_type === 'ppt_generator' && task.result?.pdf_path) ||
                    (task.tool_type === 'chart_generator' && (task.result?.filename || task.result?.image_path))) && (
                    <Grid item xs={12}>
                      <Box sx={{ mt: 2, p: 2, bgcolor: 'success.light', borderRadius: 1 }}>
                        <Box display="flex" alignItems="center" justifyContent="space-between">
                          <Typography variant="body1" color="success.dark" sx={{ fontWeight: 'bold' }}>
                            {task.tool_type === 'ppt_generator' ? '📄 PPT文件已生成完成' : '📊 图表文件已生成完成'}
                          </Typography>
                          <Button
                            variant="contained"
                            startIcon={<DownloadIcon />}
                            onClick={handleDownload}
                            color="success"
                            size="large"
                          >
                            立即下载
                          </Button>
                        </Box>
                      </Box>
                    </Grid>
                  )}
                </Grid>
              </Paper>
            </Grid>

            {/* 任务参数 */}
            <Grid item xs={12}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  任务参数
                </Typography>
                <Box sx={{ maxHeight: '200px', overflow: 'auto' }}>
                  {formatParameters(task.parameters)}
                </Box>
              </Paper>
            </Grid>

            {/* 执行结果 */}
            {task.result && (
              <Grid item xs={12}>
                <Paper sx={{ p: 2 }}>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                    <Typography variant="h6">
                      执行结果
                    </Typography>
                  </Box>
                  <Box sx={{ maxHeight: '300px', overflow: 'auto' }}>
                    <pre style={{ 
                      whiteSpace: 'pre-wrap', 
                      wordBreak: 'break-word',
                      fontSize: '0.875rem',
                      margin: 0
                    }}>
                      {JSON.stringify(task.result, null, 2)}
                    </pre>
                  </Box>
                </Paper>
              </Grid>
            )}

            {/* 错误信息 */}
            {task.error_message && (
              <Grid item xs={12}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="h6" gutterBottom color="error">
                    错误信息
                  </Typography>
                  <Alert severity="error">
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                      {task.error_message}
                    </Typography>
                  </Alert>
                </Paper>
              </Grid>
            )}

            {/* 时间信息 */}
            <Grid item xs={12}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  时间信息
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={4}>
                    <Typography variant="body2" color="text.secondary">
                      创建时间
                    </Typography>
                    <Typography variant="body2">{formatTime(task.created_at)}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <Typography variant="body2" color="text.secondary">
                      更新时间
                    </Typography>
                    <Typography variant="body2">{formatTime(task.updated_at)}</Typography>
                  </Grid>
                  {task.started_at && (
                    <Grid item xs={12} sm={4}>
                      <Typography variant="body2" color="text.secondary">
                        开始时间
                      </Typography>
                      <Typography variant="body2">{formatTime(task.started_at)}</Typography>
                    </Grid>
                  )}
                  {task.completed_at && (
                    <Grid item xs={12} sm={4}>
                      <Typography variant="body2" color="text.secondary">
                        完成时间
                      </Typography>
                      <Typography variant="body2">{formatTime(task.completed_at)}</Typography>
                    </Grid>
                  )}
                </Grid>
              </Paper>
            </Grid>
          </Grid>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>
          关闭
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TaskDetail; 