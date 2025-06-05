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
  TextareaAutosize,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  Description as DocumentIcon,
  Slideshow as SlideshowIcon,
  Download as DownloadIcon,
  Preview as PreviewIcon,
  Settings as SettingsIcon,
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
      id={`ppt-tabpanel-${index}`}
      aria-labelledby={`ppt-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

/**
 * PPT 生成器组件
 * 提供文档上传、文本输入、模板选择等功能
 */
const PPTGenerator: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(false);
  const [generationStatus, setGenerationStatus] = useState<'idle' | 'processing' | 'success' | 'error'>('idle');
  const [resultUrl, setResultUrl] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 表单数据
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    input_type: 'text_description',
    theme: 'academic',
    language: 'zh-CN',
    slides_count: 10,
    include_outline: true,
    include_references: true,
    font_size: 'medium',
    color_scheme: 'blue',
    main_tex_filename: 'main.tex', // 主LaTeX文件名
    use_ucas_style: false, // UCAS风格选项
  });

  // 上传的文件
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [fileContent, setFileContent] = useState<string>('');

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  // 检查内容是否准备就绪
  const isContentReady = (): boolean => {
    switch (formData.input_type) {
      case 'text_description':
        return formData.content.trim().length > 0;
      case 'document_content':
        return uploadedFile !== null || formData.content.trim().length > 0;
      case 'latex_project':
        return uploadedFile !== null && formData.main_tex_filename.trim().length > 0;
      default:
        return false;
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // 根据输入类型检查文件类型
    if (formData.input_type === 'latex_project') {
      const fileName = file.name.toLowerCase();
      if (!fileName.endsWith('.zip') && !fileName.endsWith('.tar.gz') && !fileName.endsWith('.tgz')) {
        alert('请选择 .zip、.tar.gz 或 .tgz 文件');
        return;
      }
    }

    setUploadedFile(file);
    
    // 如果标题为空，使用文件名作为标题
    if (!formData.title) {
      setFormData(prev => ({
        ...prev,
        title: file.name.replace(/\.(zip|tar\.gz|tgz)$/i, '')
      }));
    }

    // 如果是LaTeX项目，自动检测主tex文件
    if (formData.input_type === 'latex_project') {
      try {
        console.log('开始检测压缩文件中的LaTeX文件...');
        const detectedInfo = await detectTexFilesInArchive(file);
        
        if (detectedInfo.success && detectedInfo.suggested_main_tex) {
          setFormData(prev => ({
            ...prev,
            main_tex_filename: detectedInfo.suggested_main_tex
          }));
          console.log('自动检测到主LaTeX文件:', detectedInfo.suggested_main_tex);
          console.log('找到的所有tex文件:', detectedInfo.tex_files);
        } else {
          // 使用默认值
          setFormData(prev => ({
            ...prev,
            main_tex_filename: 'main.tex'
          }));
          console.warn('未能自动检测到LaTeX文件，使用默认值');
        }
      } catch (error) {
        console.error('检测tex文件失败:', error);
        // 使用默认值
        setFormData(prev => ({
          ...prev,
          main_tex_filename: 'main.tex'
        }));
        alert('检测LaTeX文件失败，请手动指定主文件名');
      }
    }

    // 如果是文档内容且是tex文件，读取内容
    if (formData.input_type === 'document_content' && file.name.endsWith('.tex')) {
      try {
        const content = await file.text();
        setFileContent(content);
        setFormData(prev => ({
          ...prev,
          content: content
        }));
      } catch (error) {
        console.error('读取文件失败:', error);
        alert('读取文件失败，请重试');
        setUploadedFile(null);
      }
    }
  };

  // 检测压缩文件中的LaTeX文件
  const detectTexFilesInArchive = async (archiveFile: File): Promise<any> => {
    try {
      const formData = new FormData();
      formData.append('archive_file', archiveFile);

      const response = await fetch('http://localhost:8002/detect_tex_files', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`检测失败 (${response.status}): ${errorText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('调用检测接口失败:', error);
      throw error;
    }
  };

  const handleResetFile = () => {
    setUploadedFile(null);
    setFileContent('');
    setFormData(prev => ({
      ...prev,
      content: ''
    }));
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleGenerate = async () => {
    try {
      setLoading(true);
      setGenerationStatus('processing');

      // 如果是LaTeX项目模式，先上传文件再通过后端API创建任务
      if (formData.input_type === 'latex_project' && uploadedFile) {
        try {
          console.log('开始LaTeX项目模式 - 先上传文件到后端');
          
          // 先上传压缩文件到后端
          const uploadResponse = await apiService.uploadFile(uploadedFile);
          const uploadedFilePath = uploadResponse.data.path;
          
          console.log('文件上传成功:', uploadedFilePath);

          // 通过后端API创建LaTeX转换任务
          const taskData = {
            title: formData.title || '未命名PPT',
            description: `LaTeX项目转换为PPT演示文稿`,
            tool_type: 'ppt_generator',
            parameters: {
              content: `LaTeX项目文件: ${uploadedFilePath}`,
              title: formData.title || '未命名PPT',
              input_type: 'latex_project',
              main_tex_filename: formData.main_tex_filename,
              uploaded_file_path: uploadedFilePath,
              theme: formData.theme,
              language: formData.language,
              slides_count: formData.slides_count,
              color_scheme: formData.color_scheme,
              include_outline: formData.include_outline,
              include_references: formData.include_references,
              font_size: formData.font_size,
              use_ucas_style: formData.use_ucas_style
            }
          };

          console.log('创建LaTeX转换任务:', taskData);

          const response = await apiService.createTask(taskData);
          const task = response.data;
          console.log('LaTeX转换任务已创建:', task);

          // 轮询检查任务状态
          const checkTaskStatus = async () => {
            const maxAttempts = 100; // 最多检查100次 (约5分钟)
            let attempts = 0;

            while (attempts < maxAttempts) {
              try {
                const statusResponse = await apiService.getTask(task.id);
                const taskInfo = statusResponse.data;
                
                if (taskInfo.status === 'completed') {
                  console.log('LaTeX转换任务完成:', taskInfo);
                  setGenerationStatus('success');
                  
                  // 检查是否有PDF文件路径
                  if (taskInfo.result?.pdf_path) {
                    const fullPath = taskInfo.result.pdf_path.replace(/\\/g, '/');
                    const filename = fullPath.split('/').pop() || 'presentation.pdf';
                    setResultUrl(`http://localhost:8002/download/${filename}`);
                  }
                  return;
                } else if (taskInfo.status === 'failed') {
                  console.error('LaTeX转换任务失败:', taskInfo.error_message);
                  throw new Error(taskInfo.error_message || 'LaTeX转换失败');
                }
                
                // 任务还在进行中，等待3秒后再次检查
                await new Promise(resolve => setTimeout(resolve, 3000));
                attempts++;
              } catch (error) {
                console.error('检查LaTeX转换任务状态失败:', error);
                attempts++;
                await new Promise(resolve => setTimeout(resolve, 3000));
              }
            }
            
            throw new Error('LaTeX转换任务超时，请稍后在任务管理中查看结果');
          };

          await checkTaskStatus();
          return;
        } catch (error) {
          console.error('LaTeX项目PPT生成失败:', error);
          throw error;
        }
      }

      // 其他模式使用后端API创建任务
      console.log('开始通过后端API创建PPT生成任务，输入类型:', formData.input_type);
      let content = formData.content;
      
      // 如果有上传文件且不是tex文件，读取文件内容
      if (uploadedFile && !uploadedFile.name.endsWith('.tex')) {
        if (uploadedFile.name.endsWith('.txt') || uploadedFile.name.endsWith('.md')) {
          const fileContent = await uploadedFile.text();
          content = fileContent;
          console.log('读取文件内容:', fileContent.substring(0, 200) + '...');
        } else {
          // 对于其他文件类型，先上传文件
          const uploadResponse = await apiService.uploadFile(uploadedFile);
          content = `[文档文件: ${uploadResponse.data.filename}]\n\n${content}`;
        }
      }

      console.log('准备通过后端创建任务，内容长度:', content.length);
      console.log('生成参数:', {
        title: formData.title || '未命名PPT',
        theme: formData.theme,
        language: formData.language,
        slides_count: formData.slides_count
      });

      // 通过后端API创建PPT生成任务
      const taskData = {
        title: formData.title || '未命名PPT',
        description: `生成PPT演示文稿 - ${formData.theme}主题`,
        tool_type: 'ppt_generator',
        parameters: {
          content: content,
          title: formData.title || '未命名PPT',
          theme: formData.theme,
          language: formData.language,
          slides_count: formData.slides_count,
              input_type: formData.input_type,
              color_scheme: formData.color_scheme,
              include_outline: formData.include_outline,
              include_references: formData.include_references,
              font_size: formData.font_size,
              use_ucas_style: formData.use_ucas_style
        }
      };

      const response = await apiService.createTask(taskData);
      const task = response.data;
      console.log('任务已创建:', task);

      // 轮询检查任务状态
      const checkTaskStatus = async () => {
        const maxAttempts = 100; // 最多检查100次 (约5分钟)
        let attempts = 0;

        while (attempts < maxAttempts) {
          try {
            const statusResponse = await apiService.getTask(task.id);
            const taskInfo = statusResponse.data;
            
            if (taskInfo.status === 'completed') {
              console.log('任务完成:', taskInfo);
              setGenerationStatus('success');
              
              // 检查是否有PDF文件路径
              if (taskInfo.result?.pdf_path) {
                const fullPath = taskInfo.result.pdf_path.replace(/\\/g, '/');
                const filename = fullPath.split('/').pop() || 'presentation.pdf';
                setResultUrl(`http://localhost:8002/download/${filename}`);
              }
              return;
            } else if (taskInfo.status === 'failed') {
              console.error('任务失败:', taskInfo.error_message);
              throw new Error(taskInfo.error_message || '任务执行失败');
            }
            
            // 任务还在进行中，等待3秒后再次检查
            await new Promise(resolve => setTimeout(resolve, 3000));
            attempts++;
          } catch (error) {
            console.error('检查任务状态失败:', error);
            attempts++;
            await new Promise(resolve => setTimeout(resolve, 3000));
          }
        }
        
        throw new Error('任务超时，请稍后在任务管理中查看结果');
      };

      await checkTaskStatus();

    } catch (error) {
      console.error('生成PPT失败:', error);
      setGenerationStatus('error');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      title: '',
      content: '',
      input_type: 'text_description',
      theme: 'academic',
      language: 'zh-CN',
      slides_count: 10,
      include_outline: true,
      include_references: true,
      font_size: 'medium',
      color_scheme: 'blue',
      main_tex_filename: 'main.tex',
      use_ucas_style: false,
    });
    setUploadedFile(null);
    setFileContent('');
    setGenerationStatus('idle');
    setResultUrl('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  /**
   * 获取内容字段的标签和提示
   */
  const getContentFieldInfo = () => {
    switch (formData.input_type) {
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

  /**
   * 获取文件接受类型
   */
  const getFileAcceptTypes = () => {
    switch (formData.input_type) {
      case 'latex_project':
        return '.zip,.tar.gz,.tgz';
      case 'document_content':
        return '.txt,.md,.docx,.pdf,.tex';
      default:
        return '';
    }
  };

  const contentInfo = getContentFieldInfo();

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 600 }}>
          📊 PPT 生成器
        </Typography>
        <Typography variant="body1" color="text.secondary">
          基于文档或文本内容生成专业的 LaTeX Beamer PPT
        </Typography>
      </Box>

      {/* 状态提示 */}
      {generationStatus === 'processing' && (
        <Alert severity="info" sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography>正在生成PPT，请稍候...</Typography>
            <LinearProgress sx={{ flexGrow: 1 }} />
          </Box>
        </Alert>
      )}

      {generationStatus === 'success' && (
        <Alert severity="success" sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
            <Typography sx={{ display: 'flex', alignItems: 'center' }}>
              PPT生成成功！
            </Typography>
            {resultUrl && (
              <Button
                size="small"
                startIcon={<DownloadIcon sx={{ fontSize: '16px' }} />}
                onClick={() => {
                  const link = document.createElement('a');
                  link.href = resultUrl;
                  link.download = formData.title ? `${formData.title}.pdf` : 'presentation.pdf';
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
                下载PPT
              </Button>
            )}
          </Box>
        </Alert>
      )}

      {generationStatus === 'error' && (
        <Alert severity="error" sx={{ mb: 3 }}>
          PPT生成失败，请检查输入内容并重试
        </Alert>
      )}

      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab icon={<DocumentIcon />} label="内容输入" />
            <Tab icon={<SettingsIcon />} label="样式设置" />
            <Tab icon={<PreviewIcon />} label="预览生成" />
          </Tabs>
        </Box>

        {/* 内容输入 */}
        <TabPanel value={tabValue} index={0}>
          <CardContent>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="PPT标题"
                  value={formData.title}
                  onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="请输入PPT标题"
                />
              </Grid>

              <Grid item xs={12}>
                <FormControl fullWidth>
                  <InputLabel>输入类型</InputLabel>
                  <Select
                    value={formData.input_type}
                    label="输入类型"
                    onChange={(e) => {
                      setFormData(prev => ({ ...prev, input_type: e.target.value, content: '' }));
                      setUploadedFile(null);
                      setFileContent('');
                      if (fileInputRef.current) {
                        fileInputRef.current.value = '';
                      }
                    }}
                  >
                    <MenuItem value="text_description">文字描述</MenuItem>
                    <MenuItem value="document_content">文档内容</MenuItem>
                    <MenuItem value="latex_project">LaTeX 项目</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              {/* 文件上传区域 - 对于文档内容和LaTeX项目 */}
              {(formData.input_type === 'document_content' || formData.input_type === 'latex_project') && (
                <Grid item xs={12}>
                  <Typography variant="h6" gutterBottom>
                    文件上传
                  </Typography>
                  
                  <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleFileUpload}
                      accept={getFileAcceptTypes()}
                      style={{ display: 'none' }}
                    />
                    <Button
                      variant="outlined"
                      startIcon={<UploadIcon />}
                      onClick={() => fileInputRef.current?.click()}
                    >
                      {formData.input_type === 'latex_project' ? '上传压缩文件' : '上传文档'}
                    </Button>
                    {uploadedFile && (
                      <Chip
                        label={`${uploadedFile.name} (${(uploadedFile.size / 1024).toFixed(1)}KB)`}
                        onDelete={handleResetFile}
                        color="primary"
                      />
                    )}
                  </Box>

                  {/* LaTeX项目特有的主文件名显示 */}
                  {formData.input_type === 'latex_project' && uploadedFile && (
                    <Box sx={{ mb: 2 }}>
                      <TextField
                        fullWidth
                        label="检测到的主LaTeX文件"
                        value={formData.main_tex_filename}
                        onChange={(e) => setFormData(prev => ({ ...prev, main_tex_filename: e.target.value }))}
                        placeholder="main.tex"
                        helperText="自动检测的主LaTeX文件名，可手动修改"
                        size="small"
                      />
                    </Box>
                  )}

                  {uploadedFile && (
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="caption" color="success.main" sx={{ display: 'block' }}>
                        ✅ 已选择文件: {uploadedFile.name} ({Math.round(uploadedFile.size / 1024)} KB)
                      </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                        {formData.input_type === 'latex_project' 
                          ? '压缩文件将被解压，所有资源文件将一起编译' 
                          : '文件内容已自动加载'}
                      </Typography>
                    </Box>
                  )}
                  
                  {!uploadedFile && (
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
                      {formData.input_type === 'latex_project' 
                        ? '支持上传包含LaTeX文件和资源文件（图片、数据等）的压缩包（.zip、.tar.gz、.tgz）'
                        : '支持上传文档文件，内容将自动读取并用于生成PPT'}
                    </Typography>
                  )}
                </Grid>
              )}

              {/* 文本输入区域 - 仅在没有上传文件或文字描述模式时显示 */}
              {(formData.input_type === 'text_description' || 
                (formData.input_type === 'document_content' && !uploadedFile)) && (
                <Grid item xs={12}>
                  <Typography variant="h6" gutterBottom>
                    {formData.input_type === 'text_description' ? '文字描述' : '文档内容输入'}
                  </Typography>
                  <Box>
                    <TextareaAutosize
                      minRows={8}
                      placeholder={contentInfo.placeholder}
                      value={formData.content}
                      onChange={(e) => setFormData(prev => ({ ...prev, content: e.target.value }))}
                      style={{ 
                        width: '100%', 
                        padding: '12px', 
                        borderRadius: '4px', 
                        border: '1px solid #ccc',
                        fontSize: '14px'
                      }}
                    />
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                      {formData.input_type === 'text_description' 
                        ? '支持Markdown格式，AI将自动分析内容结构并生成幻灯片'
                        : '请粘贴文档内容，或选择上传文件'}
                    </Typography>
                  </Box>
                </Grid>
              )}

              {/* 文件内容预览 - 仅在文档内容模式且有上传文件时显示 */}
              {formData.input_type === 'document_content' && uploadedFile && fileContent && (
                <Grid item xs={12}>
                  <Typography variant="h6" gutterBottom>
                    文件内容预览
                  </Typography>
                  <Box>
                    <TextareaAutosize
                      minRows={6}
                      value={formData.content}
                      onChange={(e) => setFormData(prev => ({ ...prev, content: e.target.value }))}
                      placeholder="文件内容将在这里显示..."
                      style={{ 
                        width: '100%', 
                        padding: '12px', 
                        borderRadius: '4px', 
                        border: '1px solid #ccc',
                        fontFamily: 'monospace',
                        fontSize: '14px'
                      }}
                    />
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                      文件内容已加载，可以编辑后生成PPT
                    </Typography>
                  </Box>
                </Grid>
              )}
            </Grid>
          </CardContent>
        </TabPanel>

        {/* 样式设置 */}
        <TabPanel value={tabValue} index={1}>
          <CardContent>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>PPT主题</InputLabel>
                  <Select
                    value={formData.theme}
                    label="PPT主题"
                    onChange={(e) => setFormData(prev => ({ ...prev, theme: e.target.value }))}
                  >
                    <MenuItem value="academic">学术风格</MenuItem>
                    <MenuItem value="business">商务风格</MenuItem>
                    <MenuItem value="modern">现代简约</MenuItem>
                    <MenuItem value="creative">创意设计</MenuItem>
                    <MenuItem value="minimal">极简风格</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>语言</InputLabel>
                  <Select
                    value={formData.language}
                    label="语言"
                    onChange={(e) => setFormData(prev => ({ ...prev, language: e.target.value }))}
                  >
                    <MenuItem value="zh-CN">中文</MenuItem>
                    <MenuItem value="en-US">English</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="幻灯片数量"
                  value={formData.slides_count}
                  onChange={(e) => setFormData(prev => ({ ...prev, slides_count: parseInt(e.target.value) }))}
                  inputProps={{ min: 5, max: 50 }}
                />
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
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  高级选项
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <label>
                    <input
                      type="checkbox"
                      checked={formData.include_outline}
                      onChange={(e) => setFormData(prev => ({ ...prev, include_outline: e.target.checked }))}
                    />
                    <Typography component="span" sx={{ ml: 1 }}>
                      包含目录页
                    </Typography>
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={formData.include_references}
                      onChange={(e) => setFormData(prev => ({ ...prev, include_references: e.target.checked }))}
                    />
                    <Typography component="span" sx={{ ml: 1 }}>
                      包含参考文献页
                    </Typography>
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={formData.use_ucas_style}
                      onChange={(e) => setFormData(prev => ({ ...prev, use_ucas_style: e.target.checked }))}
                    />
                    <Typography component="span" sx={{ ml: 1 }}>
                      使用UCAS风格（中国科学院大学）
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
                生成预览
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography variant="body2" color="text.secondary">
                    标题: {formData.title || '未设置'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    输入类型: {formData.input_type}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    主题: {formData.theme}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    幻灯片数量: {formData.slides_count}
                  </Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="body2" color="text.secondary">
                    语言: {formData.language}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    配色: {formData.color_scheme}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    内容来源: {uploadedFile ? `文件: ${uploadedFile.name}` : '文本输入'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    内容长度: {formData.content.length} 字符
                  </Typography>
                </Grid>
              </Grid>
            </Paper>

            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
              <Button
                variant="outlined"
                onClick={resetForm}
                disabled={loading}
              >
                重置
              </Button>
              <Button
                variant="contained"
                size="large"
                startIcon={<SlideshowIcon />}
                onClick={handleGenerate}
                disabled={loading || !isContentReady()}
              >
                {loading ? '生成中...' : '生成PPT'}
              </Button>
            </Box>
          </CardContent>
        </TabPanel>
      </Card>
    </Box>
  );
};

export default PPTGenerator; 