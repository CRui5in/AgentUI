import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  TextField,
  Card,
  CardContent,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
  LinearProgress,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextareaAutosize,
} from '@mui/material';
import {
  Add as AddIcon,
  CheckCircle as CompletedIcon,
  Schedule as PendingIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  Visibility as ViewIcon,
} from '@mui/icons-material';
import { apiService } from '../services/apiService';
import TaskDetail from './TaskDetail';

/**
 * 任务接口
 */
interface Task {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  tool_type: string;
  parameters: Record<string, any>;
  result?: any;
  created_at: string;
  updated_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
}

/**
 * 任务管理组件属性
 */
interface TaskManagerProps {
  toolType?: string;
}

/**
 * 任务管理组件
 * 提供任务的创建、查看、管理功能
 */
const TaskManager: React.FC<TaskManagerProps> = ({ toolType }) => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createSuccess, setCreateSuccess] = useState<string | null>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [fileContent, setFileContent] = useState<string>('');
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [newTask, setNewTask] = useState({
    title: '',
    description: '',
    tool_type: toolType || '',
    parameters: {} as Record<string, any>,
  });

  /**
   * 工具类型配置
   */
  const toolConfigs = {
    ppt: {
              name: 'PPT 生成器',
      fields: [
        { key: 'input_type', label: '输入类型', type: 'select', options: ['text_description', 'document_content', 'latex_project'], required: true },
        { key: 'content', label: '内容', type: 'textarea', required: false },
        { key: 'title', label: 'PPT标题', type: 'text', required: false },
        { key: 'theme', label: '主题风格', type: 'select', options: ['default', 'modern', 'academic'], required: false },
        { key: 'language', label: '语言', type: 'select', options: ['zh-CN', 'en-US'], required: false },
        { key: 'main_tex_filename', label: '主LaTeX文件名', type: 'text', required: false },
      ],
    },
    chart: {
      name: '图表生成器',
      fields: [
        { key: 'data', label: '数据 (JSON)', type: 'textarea', required: true },
        { key: 'chart_type', label: '图表类型', type: 'select', options: ['bar', 'line', 'pie', 'scatter'], required: true },
        { key: 'title', label: '图表标题', type: 'text', required: false },
        { key: 'width', label: '宽度', type: 'number', required: false },
        { key: 'height', label: '高度', type: 'number', required: false },
      ],
    },
    scheduler: {
      name: '日程管理',
      fields: [
        { key: 'title', label: '事件标题', type: 'text', required: true },
        { key: 'description', label: '事件描述', type: 'textarea', required: false },
        { key: 'start_time', label: '开始时间', type: 'datetime-local', required: true },
        { key: 'end_time', label: '结束时间', type: 'datetime-local', required: false },
        { key: 'reminder_minutes', label: '提前提醒(分钟)', type: 'number', required: false },
      ],
    },
    'api-docs': {
      name: 'API 文档生成器',
      fields: [
        { key: 'source_path', label: '源代码路径', type: 'text', required: true },
        { key: 'output_format', label: '输出格式', type: 'select', options: ['markdown', 'html'], required: true },
        { key: 'include_private', label: '包含私有方法', type: 'checkbox', required: false },
      ],
    },
  };

  /**
   * 加载任务列表
   */
  const loadTasks = async () => {
    try {
      setLoading(true);
      const response = await apiService.getTasks(toolType);
      setTasks(response.data);
    } catch (error) {
      console.error('加载任务失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 检查是否有活跃任务
  const hasActiveTasks = tasks.some(task => task.status === 'running' || task.status === 'pending');

  useEffect(() => {
    // 初始加载
    loadTasks();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [toolType]); // 只在 toolType 变化时重新加载

  useEffect(() => {
    // 设置自动刷新 - 根据是否有活跃任务调整频率
    const refreshInterval = hasActiveTasks ? 10000 : 60000; // 有活跃任务时10秒，否则60秒
    
    const interval = setInterval(() => {
      if (hasActiveTasks) {
        console.log('检测到活跃任务，刷新任务列表...');
      } else {
        console.log('定期刷新任务列表...');
      }
      loadTasks();
    }, refreshInterval);

    // 页面可见性变化时刷新
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        console.log('页面重新可见，刷新任务列表...');
        loadTasks();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    // 清理函数
    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasActiveTasks]); // 只在活跃任务状态变化时重新设置定时器

  /**
   * 查看任务详情
   */
  const handleViewTask = (taskId: string) => {
    setSelectedTaskId(taskId);
    setDetailDialogOpen(true);
  };

  /**
   * 关闭任务详情对话框
   */
  const handleCloseDetail = () => {
    setDetailDialogOpen(false);
    setSelectedTaskId(null);
  };

  /**
   * 处理文件上传
   */
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const inputType = newTask.parameters['input_type'] || '';

    // 根据输入类型检查文件类型
    if (inputType === 'latex_project') {
      const fileName = file.name.toLowerCase();
      if (!fileName.endsWith('.zip') && !fileName.endsWith('.tar.gz') && !fileName.endsWith('.tgz')) {
        setCreateError('请选择 .zip、.tar.gz 或 .tgz 文件');
        return;
      }
    }

    setUploadedFile(file);
    setCreateError(null);

    try {
      // 如果是LaTeX项目，自动检测主tex文件
      if (inputType === 'latex_project') {
        // 简化实现，使用默认值
        setNewTask(prev => ({
          ...prev,
          parameters: {
            ...prev.parameters,
            main_tex_filename: 'main.tex'
          }
        }));
      }

      // 如果是文档内容且是tex文件，读取内容
      if (inputType === 'document_content' && file.name.endsWith('.tex')) {
        const content = await file.text();
        setFileContent(content);
        
        setNewTask(prev => ({
          ...prev,
          parameters: {
            ...prev.parameters,
            content: content
          }
        }));
      }
      
      console.log('文件上传成功:', file.name);
    } catch (error) {
      console.error('读取文件失败:', error);
      setCreateError('读取文件失败，请重试');
      setUploadedFile(null);
    }
  };

  /**
   * 重置文件上传
   */
  const handleResetFile = () => {
    setUploadedFile(null);
    setFileContent('');
    setNewTask(prev => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        content: ''
      }
    }));
  };

  /**
   * 创建新任务
   */
  const handleCreateTask = async () => {
    try {
      setCreateLoading(true);
      setCreateError(null);
      setCreateSuccess(null);
      
      const response = await apiService.createTask(newTask);
      
      // 显示成功消息但不关闭对话框
      setCreateSuccess(`任务已创建成功！任务ID: ${response.data.id}。请在任务列表中查看生成进度和结果。`);
      
      // 重置表单
      setNewTask({
        title: '',
        description: '',
        tool_type: toolType || '',
        parameters: {},
      });
      setUploadedFile(null);
      setFileContent('');
      
      // 立即刷新任务列表
      await loadTasks();
      
    } catch (error: any) {
      console.error('创建任务失败:', error);
      const errorMessage = error.response?.data?.detail || error.message || '创建任务失败，请稍后重试';
      setCreateError(errorMessage);
    } finally {
      setCreateLoading(false);
    }
  };

  /**
   * 重试失败的任务
   */
  const handleRetryTask = async (taskId: string) => {
    try {
      await apiService.retryTask(taskId);
      loadTasks();
    } catch (error) {
      console.error('重试任务失败:', error);
    }
  };

  /**
   * 删除任务
   */
  const handleDeleteTask = async (taskId: string) => {
    if (window.confirm('确定要删除这个任务吗？此操作不可撤销。')) {
      try {
        await apiService.deleteTask(taskId);
        loadTasks();
      } catch (error) {
        console.error('删除任务失败:', error);
      }
    }
  };

  /**
   * 获取任务状态图标
   */
  const getStatusIcon = (task: Task) => {
    // 检查任务是否实际失败（即使状态是completed但有错误）
    const actuallyFailed = task.status === 'failed' || 
                          (task.status === 'completed' && task.result?.error) ||
                          (task.status === 'completed' && task.result?.success === false);
    
    if (actuallyFailed) {
      return <ErrorIcon color="error" />;
    }
    
    switch (task.status) {
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
  const getStatusColor = (task: Task) => {
    // 检查任务是否实际失败（即使状态是completed但有错误）
    const actuallyFailed = task.status === 'failed' || 
                          (task.status === 'completed' && task.result?.error) ||
                          (task.status === 'completed' && task.result?.success === false);
    
    if (actuallyFailed) {
      return 'error';
    }
    
    switch (task.status) {
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
   * 获取内容字段的标签和提示
   */
  const getContentFieldInfo = () => {
    const inputType = newTask.parameters['input_type'] || '';
    switch (inputType) {
      case 'text_description':
        return {
          label: '文字描述',
          placeholder: '请描述您想要生成的PPT内容，例如：\n# 人工智能发展趋势\n## 机器学习的突破\n- 深度学习技术\n- 神经网络架构\n## 应用领域\n- 自然语言处理\n- 计算机视觉'
        };
      case 'document_content':
        return {
          label: '文档内容',
          placeholder: '请粘贴完整的文档内容，AI将自动提取关键信息并生成PPT结构'
        };
      case 'latex_project':
        return {
          label: 'LaTeX 项目',
          placeholder: '请上传包含 .tex 文件和资源文件的 ZIP 压缩包'
        };
      default:
        return {
          label: '内容',
          placeholder: '请先选择输入类型'
        };
    }
  };

  // 检查任务内容是否准备就绪
  const isTaskContentReady = (): boolean => {
    const inputType = newTask.parameters['input_type'] || '';
    switch (inputType) {
      case 'text_description':
        return (newTask.parameters.content || '').trim().length > 0;
      case 'document_content':
        return uploadedFile !== null || (newTask.parameters.content || '').trim().length > 0;
      case 'latex_project':
        return uploadedFile !== null && (newTask.parameters.main_tex_filename || '').trim().length > 0;
      default:
        return false;
    }
  };

  /**
   * 渲染参数输入字段
   */
  const renderParameterField = (field: any) => {
    const value = newTask.parameters[field.key] || '';

    // 特殊处理输入类型选择
    if (field.key === 'input_type') {
      return (
        <FormControl fullWidth key={field.key} disabled={createLoading}>
          <InputLabel>{field.label}</InputLabel>
          <Select
            value={value}
            label={field.label}
            onChange={(e) =>
              setNewTask({
                ...newTask,
                parameters: { ...newTask.parameters, [field.key]: e.target.value },
              })
            }
          >
                                <MenuItem value="text_description">文字描述</MenuItem>
                    <MenuItem value="document_content">文档内容</MenuItem>
                    <MenuItem value="latex_project">LaTeX 项目</MenuItem>
          </Select>
        </FormControl>
      );
    }

    // 特殊处理内容字段
    if (field.key === 'content') {
      const contentInfo = getContentFieldInfo();
      const inputType = newTask.parameters['input_type'] || '';
      
      // 只在文字描述或文档内容且没有上传文件时显示文本输入
      if (inputType === 'text_description' || (inputType === 'document_content' && !uploadedFile)) {
        return (
          <Box key={field.key}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              {contentInfo.label} {inputType === 'text_description' ? '*' : ''}
            </Typography>
            <TextareaAutosize
              minRows={6}
              placeholder={contentInfo.placeholder}
              value={value}
              onChange={(e) =>
                setNewTask({
                  ...newTask,
                  parameters: { ...newTask.parameters, [field.key]: e.target.value },
                })
              }
              disabled={createLoading}
              style={{ 
                width: '100%', 
                padding: '12px', 
                borderRadius: '4px', 
                border: '1px solid #ccc',
                backgroundColor: createLoading ? '#f5f5f5' : 'white',
                fontSize: '14px'
              }}
            />
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              {inputType === 'text_description' 
                ? '支持Markdown格式，AI将自动分析内容结构并生成幻灯片'
                : '请粘贴文档内容，或选择上传文件'}
            </Typography>
          </Box>
        );
      }

      // 文档内容模式且有上传文件时显示文件内容预览
      if (inputType === 'document_content' && uploadedFile && fileContent) {
        return (
          <Box key={field.key}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              文件内容预览
            </Typography>
            <TextareaAutosize
              minRows={4}
              value={value}
              onChange={(e) =>
                setNewTask({
                  ...newTask,
                  parameters: { ...newTask.parameters, [field.key]: e.target.value },
                })
              }
              placeholder="文件内容将在这里显示..."
              disabled={createLoading}
              style={{ 
                width: '100%', 
                padding: '12px', 
                borderRadius: '4px', 
                border: '1px solid #ccc',
                backgroundColor: createLoading ? '#f5f5f5' : 'white',
                fontFamily: 'monospace',
                fontSize: '14px'
              }}
            />
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              文件内容已加载，可以编辑后创建任务
            </Typography>
          </Box>
        );
      }

      // LaTeX项目模式不显示内容字段
      if (inputType === 'latex_project') {
        return null;
      }

      return null;
    }

    switch (field.type) {
      case 'textarea':
        return (
          <TextareaAutosize
            key={field.key}
            minRows={3}
            placeholder={field.label}
            value={value}
            onChange={(e) =>
              setNewTask({
                ...newTask,
                parameters: { ...newTask.parameters, [field.key]: e.target.value },
              })
            }
            disabled={createLoading}
            style={{ 
              width: '100%', 
              padding: '8px', 
              borderRadius: '4px', 
              border: '1px solid #ccc',
              backgroundColor: createLoading ? '#f5f5f5' : 'white'
            }}
          />
        );
      case 'select':
        return (
          <FormControl fullWidth key={field.key} disabled={createLoading}>
            <InputLabel>{field.label}</InputLabel>
            <Select
              value={value}
              label={field.label}
              onChange={(e) =>
                setNewTask({
                  ...newTask,
                  parameters: { ...newTask.parameters, [field.key]: e.target.value },
                })
              }
            >
              {field.options.map((option: string) => (
                <MenuItem key={option} value={option}>
                  {option}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        );
      default:
        return (
          <TextField
            key={field.key}
            fullWidth
            label={field.label}
            type={field.type}
            value={value}
            onChange={(e) =>
              setNewTask({
                ...newTask,
                parameters: { ...newTask.parameters, [field.key]: e.target.value },
              })
            }
            required={field.required}
            disabled={createLoading}
            InputLabelProps={field.type === 'datetime-local' ? { shrink: true } : undefined}
          />
        );
    }
  };

  const currentToolConfig = toolType ? toolConfigs[toolType as keyof typeof toolConfigs] : null;

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
            {currentToolConfig ? `🛠️ ${currentToolConfig.name}` : '📋 任务管理'}
          </Typography>
          <Typography variant="body1" color="text.secondary">
            {currentToolConfig ? `管理和创建 ${currentToolConfig.name} 任务` : '管理所有类型的任务'}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadTasks}
          >
            刷新
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
          >
            创建任务
          </Button>
        </Box>
      </Box>

      {loading ? (
        <LinearProgress />
      ) : (
        <Grid container spacing={3}>
          {tasks.length > 0 ? (
            tasks.map((task) => (
              <Grid item xs={12} md={6} lg={4} key={task.id}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                      <Typography variant="h6" component="div">
                        {task.title}
                      </Typography>
                      <Chip
                        label={task.status === 'completed' && (task.result?.error || task.result?.success === false) ? 'failed' : task.status}
                        color={getStatusColor(task) as any}
                        size="small"
                      />
                    </Box>
                    
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      {task.description}
                    </Typography>

                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                      {getStatusIcon(task)}
                      <Typography variant="body2">
                        {task.tool_type === 'ppt' ? 'PPT 生成' : task.tool_type}
                      </Typography>
                    </Box>

                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
                      创建时间: {new Date(task.created_at).toLocaleString('zh-CN')}
                    </Typography>

                    {(task.status === 'failed' || 
                      (task.status === 'completed' && task.result?.error) ||
                      (task.status === 'completed' && task.result?.success === false)) && (
                      <Alert severity="error" sx={{ mt: 2, mb: 2 }}>
                        <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
                          任务执行失败
                        </Typography>
                        {task.error_message && (
                          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {task.error_message}
                          </Typography>
                        )}
                        {task.result?.error && (
                          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                            {task.result.error}
                          </Typography>
                        )}
                      </Alert>
                    )}

                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      <Button
                        variant="outlined"
                        size="small"
                        startIcon={<ViewIcon />}
                        onClick={() => handleViewTask(task.id)}
                      >
                        详情
                      </Button>

                      {(task.status === 'failed' || 
                        (task.status === 'completed' && task.result?.error) ||
                        (task.status === 'completed' && task.result?.success === false)) && (
                        <Button
                          variant="outlined"
                          size="small"
                          startIcon={<RefreshIcon />}
                          onClick={() => handleRetryTask(task.id)}
                        >
                          重试
                        </Button>
                      )}

                      {task.status === 'completed' && task.result && !task.result.error && (
                        <Button
                          variant="outlined"
                          size="small"
                          onClick={() => setSelectedTask(task)}
                        >
                          查看结果
                        </Button>
                      )}

                      <Button
                        variant="outlined"
                        size="small"
                        color="error"
                        onClick={() => handleDeleteTask(task.id)}
                      >
                        删除
                      </Button>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))
          ) : (
            <Grid item xs={12}>
              <Typography variant="h6" color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
                暂无任务
              </Typography>
            </Grid>
          )}
        </Grid>
      )}

      {/* 创建任务对话框 */}
      <Dialog open={createDialogOpen} onClose={() => {
        if (!createLoading) {
          setCreateDialogOpen(false);
          setCreateError(null);
          setCreateSuccess(null);
        }
      }} maxWidth="md" fullWidth>
        <DialogTitle>创建新任务</DialogTitle>
        <DialogContent>
          {createError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {createError}
            </Alert>
          )}
          {createSuccess && (
            <Alert severity="success" sx={{ mb: 2 }}>
              {createSuccess}
            </Alert>
          )}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              fullWidth
              label="任务标题"
              value={newTask.title}
              onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
              required
              disabled={createLoading}
            />
            
            <TextField
              fullWidth
              label="任务描述"
              multiline
              rows={3}
              value={newTask.description}
              onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
              disabled={createLoading}
            />

            {!toolType && (
              <FormControl fullWidth disabled={createLoading}>
                <InputLabel>工具类型</InputLabel>
                <Select
                  value={newTask.tool_type}
                  label="工具类型"
                  onChange={(e) => setNewTask({ ...newTask, tool_type: e.target.value })}
                >
                  {Object.entries(toolConfigs).map(([key, config]) => (
                    <MenuItem key={key} value={key}>
                      {config.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}

            {newTask.tool_type && toolConfigs[newTask.tool_type as keyof typeof toolConfigs] && (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Typography variant="h6">参数配置</Typography>
                {toolConfigs[newTask.tool_type as keyof typeof toolConfigs].fields.map(renderParameterField)}
                
                {/* 文件上传区域 - 对于PPT生成器的文档内容和LaTeX项目 */}
                {newTask.tool_type === 'ppt' && 
                 (newTask.parameters['input_type'] === 'document_content' || 
                  newTask.parameters['input_type'] === 'latex_project') && (
                  <Box>
                    <Typography variant="subtitle2" sx={{ mb: 1 }}>
                      文件上传
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <input
                        type="file"
                        accept={newTask.parameters['input_type'] === 'latex_project' ? '.zip,.tar.gz,.tgz' : '.txt,.md,.docx,.pdf,.tex'}
                        onChange={handleFileUpload}
                        disabled={createLoading}
                        style={{ 
                          width: '100%', 
                          padding: '12px', 
                          borderRadius: '4px', 
                          border: '1px solid #ccc',
                          backgroundColor: createLoading ? '#f5f5f5' : 'white'
                        }}
                      />
                      {uploadedFile && (
                        <Button
                          variant="outlined"
                          size="small"
                          onClick={handleResetFile}
                          disabled={createLoading}
                        >
                          重置
                        </Button>
                      )}
                    </Box>
                    
                    {/* LaTeX项目特有的主文件名显示 */}
                    {newTask.parameters['input_type'] === 'latex_project' && uploadedFile && (
                      <Box sx={{ mt: 2 }}>
                        <TextField
                          fullWidth
                          label="检测到的主LaTeX文件"
                          value={newTask.parameters['main_tex_filename'] || 'main.tex'}
                          onChange={(e) =>
                            setNewTask({
                              ...newTask,
                              parameters: { ...newTask.parameters, main_tex_filename: e.target.value },
                            })
                          }
                          placeholder="main.tex"
                          size="small"
                          disabled={createLoading}
                        />
                      </Box>
                    )}

                    {uploadedFile && (
                      <Box sx={{ mt: 1 }}>
                        <Typography variant="caption" color="success.main" sx={{ display: 'block' }}>
                          ✅ 已选择文件: {uploadedFile.name} ({Math.round(uploadedFile.size / 1024)} KB)
                        </Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                          {newTask.parameters['input_type'] === 'latex_project' 
                            ? '压缩文件将被解压，所有资源文件将一起编译' 
                            : '文件内容已自动加载'}
                        </Typography>
                      </Box>
                    )}
                    
                    {!uploadedFile && (
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                        {newTask.parameters['input_type'] === 'latex_project' 
                          ? '支持上传包含LaTeX文件和资源文件（图片、数据等）的压缩包（.zip、.tar.gz、.tgz）'
                          : '支持上传文档文件，内容将自动读取并用于生成PPT'}
                      </Typography>
                    )}
                  </Box>
                )}
              </Box>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => {
              setCreateDialogOpen(false);
              setCreateError(null);
              setCreateSuccess(null);
            }}
            disabled={createLoading}
          >
            {createSuccess ? '关闭' : '取消'}
          </Button>
          {!createSuccess && (
            <Button 
              onClick={handleCreateTask} 
              variant="contained"
              disabled={createLoading || !newTask.title.trim() || !newTask.parameters.input_type || !isTaskContentReady()}
            >
              {createLoading ? '创建中...' : '创建任务'}
            </Button>
          )}
          {createSuccess && (
            <Button 
              onClick={() => {
                setCreateSuccess(null);
                setCreateError(null);
                // 重置表单以便创建新任务
                setNewTask({
                  title: '',
                  description: '',
                  tool_type: toolType || '',
                  parameters: {},
                });
              }}
              variant="contained"
            >
              创建新任务
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* 任务结果对话框 */}
      <Dialog open={!!selectedTask} onClose={() => setSelectedTask(null)} maxWidth="lg" fullWidth>
        <DialogTitle>任务结果</DialogTitle>
        <DialogContent>
          {selectedTask && (
            <Box>
              <Typography variant="h6" gutterBottom>
                {selectedTask.title}
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {selectedTask.description}
              </Typography>
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle1" gutterBottom>
                  结果:
                </Typography>
                <pre style={{ background: '#f5f5f5', padding: '16px', borderRadius: '4px', overflow: 'auto' }}>
                  {JSON.stringify(selectedTask.result, null, 2)}
                </pre>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedTask(null)}>关闭</Button>
        </DialogActions>
      </Dialog>

      {/* 任务详情对话框 */}
      <TaskDetail
        open={detailDialogOpen}
        onClose={handleCloseDetail}
        taskId={selectedTaskId}
      />
    </Box>
  );
};

export default TaskManager; 