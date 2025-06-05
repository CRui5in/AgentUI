import React, { useState, useRef } from 'react';
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
  Alert,
  LinearProgress,
  Chip,
  Grid,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  BarChart as BarChartIcon,
  ShowChart as LineChartIcon,
  PieChart as PieChartIcon,
  ScatterPlot as ScatterIcon,
  TableChart as DataIcon,
  Palette as StyleIcon,
  Preview as PreviewIcon,
  Download as DownloadIcon,
  ExpandMore as ExpandMoreIcon,
  CloudUpload as UploadIcon,
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
      id={`chart-tabpanel-${index}`}
      aria-labelledby={`chart-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

/**
 * 图表生成器组件
 * 提供数据输入、图表类型选择、样式配置等功能
 */
const ChartGenerator: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(false);
  const [generationStatus, setGenerationStatus] = useState<'idle' | 'processing' | 'success' | 'error'>('idle');
  const [resultUrl, setResultUrl] = useState<string>('');
  const [previewData, setPreviewData] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 表单数据
  const [formData, setFormData] = useState({
    title: '',
    chart_type: 'bar',
    data_source: 'manual', // manual, csv, json
    data: '',
    x_axis: '',
    y_axis: '',
    width: 800,
    height: 600,
    theme: 'default',
    color_scheme: 'blue',
    show_legend: true,
    show_grid: true,
    show_values: false,
    animation: true,
    auto_generate: true, // 自动生成 vs 手动控制
  });

  // 上传的文件
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  // 示例数据模板
  const dataTemplates = {
    bar: `{
  "labels": ["一月", "二月", "三月", "四月", "五月"],
  "datasets": [{
    "label": "销售额",
    "data": [12, 19, 3, 5, 2]
  }]
}`,
    line: `{
  "labels": ["周一", "周二", "周三", "周四", "周五"],
  "datasets": [{
    "label": "访问量",
    "data": [65, 59, 80, 81, 56]
  }]
}`,
    pie: `{
  "labels": ["Chrome", "Firefox", "Safari", "Edge", "其他"],
  "datasets": [{
    "data": [45, 25, 15, 10, 5]
  }]
}`,
    scatter: `{
  "datasets": [{
    "label": "数据点",
    "data": [
      {"x": 10, "y": 20},
      {"x": 15, "y": 25},
      {"x": 20, "y": 30},
      {"x": 25, "y": 35}
    ]
  }]
}`,
    mermaid: `graph TD
    A[开始] --> B{是否满足条件?}
    B -->|是| C[执行操作]
    B -->|否| D[跳过]
    C --> E[结束]
    D --> E`
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setUploadedFile(file);
      setFormData(prev => ({ ...prev, data_source: 'csv' }));
      
      // 如果标题为空，使用文件名作为标题
      if (!formData.title) {
        setFormData(prev => ({
          ...prev,
          title: file.name.replace(/\.[^/.]+$/, '') + '图表'
        }));
      }
    }
  };

  const loadTemplate = (chartType: string) => {
    const template = dataTemplates[chartType as keyof typeof dataTemplates];
    if (template) {
      setFormData(prev => ({
        ...prev,
        chart_type: chartType,
        data: template,
        data_source: 'manual'
      }));
      
      // 根据图表类型解析数据进行预览
      if (chartType === 'mermaid') {
        setPreviewData({ type: 'mermaid', code: template });
      } else {
      try {
        const parsedData = JSON.parse(template);
          setPreviewData({ type: 'json', data: parsedData });
      } catch (error) {
          setPreviewData({ type: 'text', data: template });
        }
      }
    }
  };

  const handleDataChange = (newData: string) => {
    setFormData(prev => ({ ...prev, data: newData }));
    
    // 根据图表类型解析数据
    if (formData.chart_type === 'mermaid') {
      // Mermaid代码预览
      setPreviewData({ type: 'mermaid', code: newData });
    } else {
      // 尝试解析JSON数据进行预览
    try {
      const parsedData = JSON.parse(newData);
        setPreviewData({ type: 'json', data: parsedData });
      } catch (error) {
        setPreviewData({ type: 'text', data: newData });
      }
    }
  };

  const handleAIGenerate = async () => {
    try {
      setLoading(true);
      setGenerationStatus('processing');
      setResultUrl(''); // 重置图表URL，因为这次是生成数据

      // AI智能生成：通过后端调用Agent和LLM生成图表数据
      const taskData = {
        title: `AI生成图表数据: ${formData.title || formData.chart_type}`,
        description: `根据用户需求"${formData.data}"生成${formData.chart_type}类型的图表数据`,
        tool_type: 'chart_data_generator', // 专门用于生成数据的工具类型
        parameters: {
          user_requirement: formData.data, // 用户在数据配置中输入的需求
          chart_type: formData.chart_type,
          title: formData.title
        }
      };

      console.log('AI生成数据请求:', taskData);

      const response = await apiService.createTask(taskData);
      
      // 轮询任务状态
      const taskId = response.data.id;
      const maxWaitTime = 60000; // 60秒
      const checkInterval = 3000; // 3秒
      let waited = 0;
      
      const checkStatus = async () => {
        try {
          const statusResponse = await apiService.getTask(taskId);
          const task = statusResponse.data;
          
          if (task.status === 'completed') {
            setGenerationStatus('success');
            
            // 将生成的数据填充到数据配置输入框中
            if (task.result && task.result.generated_data) {
              const generatedData = typeof task.result.generated_data === 'string' 
                ? task.result.generated_data 
                : JSON.stringify(task.result.generated_data, null, 2);
              
              setFormData(prev => ({ ...prev, data: generatedData }));
              
              // 更新预览数据
              handleDataChange(generatedData);
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
          setGenerationStatus('error');
          console.error('检查任务状态失败:', error);
        }
      };
      
      setTimeout(checkStatus, checkInterval);

    } catch (error) {
      console.error('AI生成数据失败:', error);
      setGenerationStatus('error');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    try {
      setLoading(true);
      setGenerationStatus('processing');

      let chartData = formData.data;
      
      // 如果有上传文件，先处理文件
      if (uploadedFile && formData.data_source === 'csv') {
        const uploadResponse = await apiService.uploadFile(uploadedFile);
        chartData = `[CSV文件: ${uploadResponse.data.filename}]`;
      }

      const taskData = {
        title: formData.title || '未命名图表',
        description: `生成${formData.chart_type}类型的图表，尺寸${formData.width}x${formData.height}`,
        tool_type: 'chart_generator',
        parameters: {
          chart_type: formData.chart_type,
          data: chartData,
          title: formData.title,
          width: formData.width,
          height: formData.height,
          theme: formData.theme,
          color_scheme: formData.color_scheme,
          style_options: {
            show_legend: formData.show_legend,
            show_grid: formData.show_grid,
            show_values: formData.show_values,
            animation: formData.animation
          }
        }
      };

      const response = await apiService.createTask(taskData);
      
      // 轮询任务状态
      const taskId = response.data.id;
      const maxWaitTime = 60000; // 60秒
      const checkInterval = 2000; // 2秒
      let waited = 0;
      
      const checkStatus = async () => {
        try {
          const statusResponse = await apiService.getTask(taskId);
          const task = statusResponse.data;
          
          if (task.status === 'completed') {
      setGenerationStatus('success');
            if (task.result && (task.result.filename || task.result.image_path)) {
              // 优先使用filename，如果没有则从image_path提取
              const filename = task.result.filename || task.result.image_path.split('/').pop();
              setResultUrl(`http://localhost:8003/download/${filename}`);
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
          setGenerationStatus('error');
          console.error('检查任务状态失败:', error);
        }
      };
      
      setTimeout(checkStatus, checkInterval);

    } catch (error) {
      console.error('生成图表失败:', error);
      setGenerationStatus('error');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      title: '',
      chart_type: 'bar',
      data_source: 'manual',
      data: '',
      x_axis: '',
      y_axis: '',
      width: 800,
      height: 600,
      theme: 'default',
      color_scheme: 'blue',
      show_legend: true,
      show_grid: true,
      show_values: false,
      animation: true,
      auto_generate: true,
    });
    setUploadedFile(null);
    setGenerationStatus('idle');
    setResultUrl('');
    setPreviewData(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 600 }}>
          📊 图表生成器
        </Typography>
        <Typography variant="body1" color="text.secondary">
          基于数据生成各种类型的专业图表，支持多种数据源和自定义样式
        </Typography>
      </Box>

      {/* 状态提示 */}
      {generationStatus === 'processing' && (
        <Alert severity="info" sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography>
              {resultUrl ? '正在生成图表，请稍候...' : '正在生成数据，请稍候...'}
            </Typography>
            <LinearProgress sx={{ flexGrow: 1 }} />
          </Box>
        </Alert>
      )}

      {generationStatus === 'success' && resultUrl && (
        <Alert severity="success" sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
            <Typography sx={{ display: 'flex', alignItems: 'center' }}>
          图表生成成功！
            </Typography>
            <Button
              size="small"
              startIcon={<DownloadIcon sx={{ fontSize: '16px' }} />}
              onClick={() => {
                const link = document.createElement('a');
                link.href = resultUrl;
                link.download = formData.title ? `${formData.title}.png` : 'chart.png';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
              }}
              variant="outlined"
              color="success"
              sx={{ 
                fontSize: '12px',
                padding: '4px 8px',
                minWidth: 'auto',
                height: '24px'
              }}
            >
              下载图表
            </Button>
          </Box>
        </Alert>
          )}

      {generationStatus === 'success' && !resultUrl && (
        <Alert severity="success" sx={{ mb: 3 }}>
          数据生成成功！请检查下方数据配置，然后点击"自动生成图表"按钮生成图表。
        </Alert>
      )}

      {generationStatus === 'error' && (
        <Alert severity="error" sx={{ mb: 3 }}>
          操作失败，请检查输入内容并重试
        </Alert>
      )}

      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab icon={<DataIcon />} label="数据输入" />
            <Tab icon={<StyleIcon />} label="样式设置" />
            <Tab icon={<PreviewIcon />} label="预览生成" />
          </Tabs>
        </Box>

        {/* 数据输入 */}
        <TabPanel value={tabValue} index={0}>
          <CardContent>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="图表标题"
                  value={formData.title}
                  onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="请输入图表标题"
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>图表类型</InputLabel>
                  <Select
                    value={formData.chart_type}
                    label="图表类型"
                    onChange={(e) => setFormData(prev => ({ ...prev, chart_type: e.target.value }))}
                  >
                    <MenuItem value="bar">
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <BarChartIcon />
                        柱状图
                      </Box>
                    </MenuItem>
                    <MenuItem value="line">
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <LineChartIcon />
                        折线图
                      </Box>
                    </MenuItem>
                    <MenuItem value="pie">
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <PieChartIcon />
                        饼图
                      </Box>
                    </MenuItem>
                    <MenuItem value="scatter">
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <ScatterIcon />
                        散点图
                      </Box>
                    </MenuItem>
                    <MenuItem value="mermaid">
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <ScatterIcon />
                        Mermaid图表
                      </Box>
                    </MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>数据来源</InputLabel>
                  <Select
                    value={formData.data_source}
                    label="数据来源"
                    onChange={(e) => setFormData(prev => ({ ...prev, data_source: e.target.value }))}
                  >
                    <MenuItem value="manual">手动输入</MenuItem>
                    <MenuItem value="csv">CSV文件</MenuItem>
                    <MenuItem value="json">JSON文件</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              {formData.data_source !== 'manual' && (
                <Grid item xs={12}>
                  <Box>
                    <Typography variant="h6" gutterBottom>
                      上传数据文件
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                      <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileUpload}
                        accept={formData.data_source === 'csv' ? '.csv' : '.json'}
                        style={{ display: 'none' }}
                      />
                      <Button
                        variant="outlined"
                        startIcon={<UploadIcon />}
                        onClick={() => fileInputRef.current?.click()}
                      >
                        选择{formData.data_source.toUpperCase()}文件
                      </Button>
                      {uploadedFile && (
                        <Chip
                          label={`${uploadedFile.name} (${(uploadedFile.size / 1024).toFixed(1)}KB)`}
                          onDelete={() => setUploadedFile(null)}
                          color="primary"
                        />
                      )}
                    </Box>
                  </Box>
                </Grid>
              )}

              <Grid item xs={12}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6">
                    数据配置
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => loadTemplate('bar')}
                    >
                      柱状图模板
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => loadTemplate('line')}
                    >
                      折线图模板
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => loadTemplate('pie')}
                    >
                      饼图模板
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => loadTemplate('mermaid')}
                    >
                      Mermaid模板
                    </Button>
                    <Button
                      size="small"
                      variant="contained"
                      color="secondary"
                      onClick={() => handleAIGenerate()}
                      disabled={loading || !formData.data.trim()}
                      title="根据输入的需求描述，使用AI生成图表数据"
                    >
                      AI生成数据
                    </Button>
                  </Box>
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  💡 <strong>使用说明：</strong>
                  <br />• <strong>模板按钮</strong>：加载对应图表类型的示例数据到输入框
                  <br />• <strong>AI生成数据</strong>：输入需求描述，AI自动生成图表数据到输入框
                  <br />• <strong>手动输入</strong>：直接在输入框中编写JSON/Mermaid代码
                  <br />• <strong>自动生成图表</strong>：使用输入框中的数据生成最终图表
                </Typography>
                <TextField
                  fullWidth
                  multiline
                  rows={10}
                  label={formData.chart_type === 'mermaid' ? "Mermaid代码" : "数据"}
                  value={formData.data}
                  onChange={(e) => handleDataChange(e.target.value)}
                  placeholder={
                    formData.chart_type === 'mermaid' 
                      ? "请输入Mermaid图表代码..." 
                      : "请输入图表数据..."
                  }
                  helperText={
                    formData.chart_type === 'mermaid'
                      ? "支持流程图、时序图、甘特图等Mermaid语法"
                      : "支持Chart.js数据格式，可以点击上方模板按钮加载示例数据"
                  }
                />
              </Grid>
            </Grid>
          </CardContent>
        </TabPanel>

        {/* 样式设置 */}
        <TabPanel value={tabValue} index={1}>
          <CardContent>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="图表宽度"
                  value={formData.width}
                  onChange={(e) => setFormData(prev => ({ ...prev, width: parseInt(e.target.value) }))}
                  inputProps={{ min: 400, max: 2000 }}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="图表高度"
                  value={formData.height}
                  onChange={(e) => setFormData(prev => ({ ...prev, height: parseInt(e.target.value) }))}
                  inputProps={{ min: 300, max: 1500 }}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>主题</InputLabel>
                  <Select
                    value={formData.theme}
                    label="主题"
                    onChange={(e) => setFormData(prev => ({ ...prev, theme: e.target.value }))}
                  >
                    <MenuItem value="default">默认</MenuItem>
                    <MenuItem value="dark">深色</MenuItem>
                    <MenuItem value="light">浅色</MenuItem>
                    <MenuItem value="minimal">极简</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>配色方案</InputLabel>
                  <Select
                    value={formData.color_scheme}
                    label="配色方案"
                    onChange={(e) => setFormData(prev => ({ ...prev, color_scheme: e.target.value }))}
                  >
                    <MenuItem value="blue">蓝色系</MenuItem>
                    <MenuItem value="green">绿色系</MenuItem>
                    <MenuItem value="red">红色系</MenuItem>
                    <MenuItem value="purple">紫色系</MenuItem>
                    <MenuItem value="orange">橙色系</MenuItem>
                    <MenuItem value="rainbow">彩虹色</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  显示选项
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <label>
                    <input
                      type="checkbox"
                      checked={formData.auto_generate}
                      onChange={(e) => setFormData(prev => ({ ...prev, auto_generate: e.target.checked }))}
                    />
                    <Typography component="span" sx={{ ml: 1 }}>
                      自动生成模式 (取消勾选可手动控制)
                    </Typography>
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={formData.show_legend}
                      onChange={(e) => setFormData(prev => ({ ...prev, show_legend: e.target.checked }))}
                    />
                    <Typography component="span" sx={{ ml: 1 }}>
                      显示图例
                    </Typography>
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={formData.show_grid}
                      onChange={(e) => setFormData(prev => ({ ...prev, show_grid: e.target.checked }))}
                    />
                    <Typography component="span" sx={{ ml: 1 }}>
                      显示网格线
                    </Typography>
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={formData.show_values}
                      onChange={(e) => setFormData(prev => ({ ...prev, show_values: e.target.checked }))}
                    />
                    <Typography component="span" sx={{ ml: 1 }}>
                      显示数值标签
                    </Typography>
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={formData.animation}
                      onChange={(e) => setFormData(prev => ({ ...prev, animation: e.target.checked }))}
                    />
                    <Typography component="span" sx={{ ml: 1 }}>
                      启用动画效果
                    </Typography>
                  </label>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </TabPanel>

        {/* 预览生成 */}
        <TabPanel value={tabValue} index={2}>
          <CardContent>
            <Paper sx={{ p: 3, mb: 3, bgcolor: 'grey.50' }}>
              <Typography variant="h6" gutterBottom>
                图表配置预览
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography variant="body2" color="text.secondary">
                    标题: {formData.title || '未设置'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    类型: {formData.chart_type}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    尺寸: {formData.width} x {formData.height}
                  </Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="body2" color="text.secondary">
                    主题: {formData.theme}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    配色: {formData.color_scheme}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    数据来源: {formData.data_source}
                  </Typography>
                </Grid>
              </Grid>
            </Paper>

            {previewData && (
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography variant="h6">
                    {previewData.type === 'mermaid' ? 'Mermaid代码预览' : '数据预览'}
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  {previewData.type === 'mermaid' ? (
                    <Box>
                      <Typography variant="subtitle2" sx={{ mb: 1 }}>Mermaid代码:</Typography>
                      <pre style={{ background: '#f5f5f5', padding: '16px', borderRadius: '4px', overflow: 'auto', fontSize: '0.9rem' }}>
                        {previewData.code}
                      </pre>
                      <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                        提示：Mermaid图表将在生成时渲染。支持流程图(graph)、时序图(sequenceDiagram)、甘特图(gantt)等
                      </Typography>
                    </Box>
                  ) : previewData.type === 'json' ? (
                  <pre style={{ background: '#f5f5f5', padding: '16px', borderRadius: '4px', overflow: 'auto' }}>
                      {JSON.stringify(previewData.data, null, 2)}
                    </pre>
                  ) : (
                    <Box>
                      <Typography variant="subtitle2" sx={{ mb: 1 }}>文本内容:</Typography>
                      <pre style={{ background: '#f5f5f5', padding: '16px', borderRadius: '4px', overflow: 'auto', fontSize: '0.9rem' }}>
                        {previewData.data}
                  </pre>
                    </Box>
                  )}
                </AccordionDetails>
              </Accordion>
            )}

            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', mt: 3 }}>
              <Button
                variant="outlined"
                onClick={resetForm}
                disabled={loading}
              >
                重置
              </Button>
              {formData.auto_generate ? (
                <Button
                  variant="contained"
                  size="large"
                  startIcon={<BarChartIcon />}
                  onClick={handleGenerate}
                  disabled={loading || !formData.data}
                >
                  {loading ? '生成中...' : '自动生成图表'}
                </Button>
              ) : (
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button
                    variant="outlined"
                    startIcon={<PreviewIcon />}
                    onClick={() => {
                      // 预览逻辑，暂时显示当前配置
                      console.log('预览配置:', formData);
                    }}
                    disabled={loading || !formData.data}
                  >
                    预览
              </Button>
              <Button
                variant="contained"
                size="large"
                startIcon={<BarChartIcon />}
                onClick={handleGenerate}
                disabled={loading || !formData.data}
              >
                    {loading ? '生成中...' : '手动生成'}
              </Button>
                </Box>
              )}
            </Box>
          </CardContent>
        </TabPanel>
      </Card>
    </Box>
  );
};

export default ChartGenerator; 