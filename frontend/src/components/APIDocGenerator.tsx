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
  FormControlLabel,
  Checkbox,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  Code as CodeIcon,
  Description as DocumentIcon,
  Settings as SettingsIcon,
  Preview as PreviewIcon,
  FolderOpen as FolderIcon,
  Download as DownloadIcon,
  ExpandMore as ExpandMoreIcon,
  GitHub as GitHubIcon,
  Api as ApiIcon,
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
      id={`api-doc-tabpanel-${index}`}
      aria-labelledby={`api-doc-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

/**
 * API 文档生成器组件
 * 提供代码仓库分析、API文档生成等功能
 */
const APIDocGenerator: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(false);
  const [generationStatus, setGenerationStatus] = useState<'idle' | 'analyzing' | 'generating' | 'success' | 'error'>('idle');
  const [resultUrl, setResultUrl] = useState<string>('');
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 表单数据
  const [formData, setFormData] = useState({
    project_name: '',
    source_type: 'local', // local, github, upload
    source_path: '',
    github_url: '',
    output_format: 'markdown',
    include_private: false,
    include_internal: false,
    include_tests: false,
    include_examples: true,
    generate_openapi: true,
    generate_postman: false,
    language: 'auto', // auto, python, javascript, java, etc.
    doc_style: 'detailed', // brief, detailed, comprehensive
  });

  // 上传的文件
  const [uploadedFiles, setUploadedFiles] = useState<FileList | null>(null);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      setUploadedFiles(files);
      // 如果项目名为空，使用第一个文件的目录名作为项目名
      if (!formData.project_name && files[0].webkitRelativePath) {
        const pathParts = files[0].webkitRelativePath.split('/');
        setFormData(prev => ({
          ...prev,
          project_name: pathParts[0] || '未命名项目'
        }));
      }
    }
  };

  const handleAnalyze = async () => {
    try {
      setLoading(true);
      setGenerationStatus('analyzing');

      let sourceData: any = {};

      // 根据源类型准备数据
      switch (formData.source_type) {
        case 'local':
          sourceData = { path: formData.source_path };
          break;
        case 'github':
          sourceData = { github_url: formData.github_url };
          break;
        case 'upload':
          if (uploadedFiles) {
            // 上传文件到服务器
            const uploadResponse = await apiService.uploadFiles(Array.from(uploadedFiles));
            sourceData = { uploaded_files: uploadResponse.data.files };
          }
          break;
      }

      const analysisData = {
        project_name: formData.project_name,
        source_type: formData.source_type,
        source_data: sourceData,
        language: formData.language,
        include_private: formData.include_private,
        include_internal: formData.include_internal,
        include_tests: formData.include_tests,
      };

      const response = await apiService.analyzeCodebase(analysisData);
      setAnalysisResult(response.data);
      setGenerationStatus('success');

    } catch (error) {
      console.error('代码分析失败:', error);
      setGenerationStatus('error');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!analysisResult) {
      await handleAnalyze();
      return;
    }

    try {
      setLoading(true);
      setGenerationStatus('generating');

      const taskData = {
        title: `${formData.project_name} API文档`,
        description: `生成${formData.project_name}项目的${formData.output_format}格式API文档`,
        tool_type: 'api-docs',
        parameters: {
          ...formData,
          analysis_result: analysisResult,
        }
      };

      const response = await apiService.createTask(taskData);
      
      setGenerationStatus('success');
      // 这里应该轮询任务状态，简化处理
      setTimeout(() => {
        const extension = formData.output_format === 'markdown' ? 'md' : 'html';
        setResultUrl(`/api/tasks/${response.data.id}/download/api-docs.${extension}`);
      }, 5000);

    } catch (error) {
      console.error('生成API文档失败:', error);
      setGenerationStatus('error');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      project_name: '',
      source_type: 'local',
      source_path: '',
      github_url: '',
      output_format: 'markdown',
      include_private: false,
      include_internal: false,
      include_tests: false,
      include_examples: true,
      generate_openapi: true,
      generate_postman: false,
      language: 'auto',
      doc_style: 'detailed',
    });
    setUploadedFiles(null);
    setGenerationStatus('idle');
    setResultUrl('');
    setAnalysisResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 600 }}>
          📚 API 文档生成器
        </Typography>
        <Typography variant="body1" color="text.secondary">
          基于代码仓库自动生成专业的 API 文档，支持多种编程语言和输出格式
        </Typography>
      </Box>

      {/* 状态提示 */}
      {generationStatus === 'analyzing' && (
        <Alert severity="info" sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography>正在分析代码结构，请稍候...</Typography>
            <LinearProgress sx={{ flexGrow: 1 }} />
          </Box>
        </Alert>
      )}

      {generationStatus === 'generating' && (
        <Alert severity="info" sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography>正在生成API文档，请稍候...</Typography>
            <LinearProgress sx={{ flexGrow: 1 }} />
          </Box>
        </Alert>
      )}

      {generationStatus === 'success' && (
        <Alert severity="success" sx={{ mb: 3 }}>
          API文档生成成功！
          {resultUrl && (
            <Button
              size="small"
              startIcon={<DownloadIcon />}
              href={resultUrl}
              download
              sx={{ ml: 2 }}
            >
              下载文档
            </Button>
          )}
        </Alert>
      )}

      {generationStatus === 'error' && (
        <Alert severity="error" sx={{ mb: 3 }}>
          处理失败，请检查输入内容并重试
        </Alert>
      )}

      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab icon={<CodeIcon />} label="代码源" />
            <Tab icon={<SettingsIcon />} label="生成设置" />
            <Tab icon={<PreviewIcon />} label="分析预览" />
          </Tabs>
        </Box>

        {/* 代码源 */}
        <TabPanel value={tabValue} index={0}>
          <CardContent>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="项目名称"
                  value={formData.project_name}
                  onChange={(e) => setFormData(prev => ({ ...prev, project_name: e.target.value }))}
                  placeholder="请输入项目名称"
                />
              </Grid>

              <Grid item xs={12}>
                <FormControl fullWidth>
                  <InputLabel>代码源类型</InputLabel>
                  <Select
                    value={formData.source_type}
                    label="代码源类型"
                    onChange={(e) => setFormData(prev => ({ ...prev, source_type: e.target.value }))}
                  >
                    <MenuItem value="local">本地路径</MenuItem>
                    <MenuItem value="github">GitHub 仓库</MenuItem>
                    <MenuItem value="upload">上传文件</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              {formData.source_type === 'local' && (
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="本地代码路径"
                    value={formData.source_path}
                    onChange={(e) => setFormData(prev => ({ ...prev, source_path: e.target.value }))}
                    placeholder="例如: /path/to/your/project"
                    InputProps={{
                      startAdornment: <FolderIcon sx={{ mr: 1, color: 'text.secondary' }} />,
                    }}
                  />
                </Grid>
              )}

              {formData.source_type === 'github' && (
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="GitHub 仓库 URL"
                    value={formData.github_url}
                    onChange={(e) => setFormData(prev => ({ ...prev, github_url: e.target.value }))}
                    placeholder="例如: https://github.com/username/repository"
                    InputProps={{
                      startAdornment: <GitHubIcon sx={{ mr: 1, color: 'text.secondary' }} />,
                    }}
                  />
                </Grid>
              )}

              {formData.source_type === 'upload' && (
                <Grid item xs={12}>
                  <Box>
                    <Typography variant="h6" gutterBottom>
                      上传代码文件
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                      <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileUpload}
                        multiple
                        {...({ webkitdirectory: "" } as any)}
                        style={{ display: 'none' }}
                      />
                      <Button
                        variant="outlined"
                        startIcon={<FolderIcon />}
                        onClick={() => fileInputRef.current?.click()}
                      >
                        选择项目文件夹
                      </Button>
                      {uploadedFiles && (
                        <Chip
                          label={`已选择 ${uploadedFiles.length} 个文件`}
                          onDelete={() => setUploadedFiles(null)}
                          color="primary"
                        />
                      )}
                    </Box>
                    <Typography variant="body2" color="text.secondary">
                      请选择包含源代码的文件夹，支持多种编程语言
                    </Typography>
                  </Box>
                </Grid>
              )}

              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>编程语言</InputLabel>
                  <Select
                    value={formData.language}
                    label="编程语言"
                    onChange={(e) => setFormData(prev => ({ ...prev, language: e.target.value }))}
                  >
                    <MenuItem value="auto">自动检测</MenuItem>
                    <MenuItem value="python">Python</MenuItem>
                    <MenuItem value="javascript">JavaScript/TypeScript</MenuItem>
                    <MenuItem value="java">Java</MenuItem>
                    <MenuItem value="csharp">C#</MenuItem>
                    <MenuItem value="go">Go</MenuItem>
                    <MenuItem value="rust">Rust</MenuItem>
                    <MenuItem value="php">PHP</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
          </CardContent>
        </TabPanel>

        {/* 生成设置 */}
        <TabPanel value={tabValue} index={1}>
          <CardContent>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>输出格式</InputLabel>
                  <Select
                    value={formData.output_format}
                    label="输出格式"
                    onChange={(e) => setFormData(prev => ({ ...prev, output_format: e.target.value }))}
                  >
                    <MenuItem value="markdown">Markdown</MenuItem>
                    <MenuItem value="html">HTML</MenuItem>
                    <MenuItem value="pdf">PDF</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>文档风格</InputLabel>
                  <Select
                    value={formData.doc_style}
                    label="文档风格"
                    onChange={(e) => setFormData(prev => ({ ...prev, doc_style: e.target.value }))}
                  >
                    <MenuItem value="brief">简洁版</MenuItem>
                    <MenuItem value="detailed">详细版</MenuItem>
                    <MenuItem value="comprehensive">完整版</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  包含内容
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={formData.include_private}
                          onChange={(e) => setFormData(prev => ({ ...prev, include_private: e.target.checked }))}
                        />
                      }
                      label="私有方法/函数"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={formData.include_internal}
                          onChange={(e) => setFormData(prev => ({ ...prev, include_internal: e.target.checked }))}
                        />
                      }
                      label="内部API"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={formData.include_tests}
                          onChange={(e) => setFormData(prev => ({ ...prev, include_tests: e.target.checked }))}
                        />
                      }
                      label="测试代码"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={formData.include_examples}
                          onChange={(e) => setFormData(prev => ({ ...prev, include_examples: e.target.checked }))}
                        />
                      }
                      label="使用示例"
                    />
                  </Grid>
                </Grid>
              </Grid>

              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  额外生成
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={formData.generate_openapi}
                          onChange={(e) => setFormData(prev => ({ ...prev, generate_openapi: e.target.checked }))}
                        />
                      }
                      label="OpenAPI 规范"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={formData.generate_postman}
                          onChange={(e) => setFormData(prev => ({ ...prev, generate_postman: e.target.checked }))}
                        />
                      }
                      label="Postman 集合"
                    />
                  </Grid>
                </Grid>
              </Grid>
            </Grid>
          </CardContent>
        </TabPanel>

        {/* 分析预览 */}
        <TabPanel value={tabValue} index={2}>
          <CardContent>
            <Paper sx={{ p: 3, mb: 3, bgcolor: 'grey.50' }}>
              <Typography variant="h6" gutterBottom>
                项目信息
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography variant="body2" color="text.secondary">
                    项目名称: {formData.project_name || '未设置'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    代码源: {formData.source_type}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    编程语言: {formData.language}
                  </Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="body2" color="text.secondary">
                    输出格式: {formData.output_format}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    文档风格: {formData.doc_style}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    包含私有API: {formData.include_private ? '是' : '否'}
                  </Typography>
                </Grid>
              </Grid>
            </Paper>

            {analysisResult && (
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography variant="h6">代码分析结果</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <pre style={{ background: '#f5f5f5', padding: '16px', borderRadius: '4px', overflow: 'auto' }}>
                    {JSON.stringify(analysisResult, null, 2)}
                  </pre>
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
              <Button
                variant="outlined"
                startIcon={<ApiIcon />}
                onClick={handleAnalyze}
                disabled={loading || !formData.project_name}
              >
                {generationStatus === 'analyzing' ? '分析中...' : '分析代码'}
              </Button>
              <Button
                variant="contained"
                size="large"
                startIcon={<DocumentIcon />}
                onClick={handleGenerate}
                disabled={loading || !formData.project_name}
              >
                {generationStatus === 'generating' ? '生成中...' : '生成文档'}
              </Button>
            </Box>
          </CardContent>
        </TabPanel>
      </Card>
    </Box>
  );
};

export default APIDocGenerator; 