import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  Button,
  Grid,
  Tabs,
  Tab,
  Switch,
  FormControlLabel,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  Divider,
  IconButton,
  Chip,
  Autocomplete,
} from '@mui/material';
import {
  Save as SaveIcon,
  Refresh as RefreshIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Info as InfoIcon,
  CheckCircle as CheckIcon,
  Download as ExportIcon,
  Upload as ImportIcon,
  RestartAlt as ResetIcon,
  ArrowBack as BackIcon,
} from '@mui/icons-material';
import configService, { 
  type LLMConfig as ConfigLLMConfig, 
  type DatabaseConfig, 
  type ServiceConfig, 
  type AppConfig 
} from '../services/configService';

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
      id={`settings-tabpanel-${index}`}
      aria-labelledby={`settings-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

interface ExtendedLLMConfig extends ConfigLLMConfig {
  endpoint?: string;
  api_version?: string;
  deployment_name?: string;
}

type LLMConfig = ExtendedLLMConfig;

interface LLMProviderConfig {
  name: string;
  description: string;
  fields: string[];
  models: string[];
  customModel?: boolean;
}

const LLM_PROVIDERS: Record<string, LLMProviderConfig> = {
  openai: {
    name: 'OpenAI',
    description: '通用OpenAI兼容接口',
    fields: ['api_key', 'base_url', 'model'],
    models: [],
    customModel: true
  },
  gpt: {
    name: 'GPT',
    description: 'OpenAI官方GPT模型',
    fields: ['api_key', 'model'],
    models: []
  },
  anthropic: {
    name: 'Anthropic',
    description: 'Claude系列模型',
    fields: ['api_key', 'model'],
    models: []
  },
  gemini: {
    name: 'Google Gemini',
    description: 'Google AI的Gemini模型',
    fields: ['api_key', 'model'],
    models: []
  },
  azure: {
    name: 'Azure OpenAI',
    description: 'Microsoft Azure上的OpenAI服务',
    fields: ['api_key', 'endpoint', 'api_version', 'deployment_name'],
    models: []
  },
  deepseek: {
    name: 'DeepSeek',
    description: 'DeepSeek AI模型',
    fields: ['api_key', 'base_url', 'model'],
    models: []
  }
};

const Settings: React.FC = () => {
  const navigate = useNavigate();
  const [tabValue, setTabValue] = useState(0);
  const [showPasswords, setShowPasswords] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle');
  
  const [testStatus, setTestStatus] = useState<{
    llm: 'idle' | 'testing' | 'success' | 'error';
    database: 'idle' | 'testing' | 'success' | 'error';
    service: 'idle' | 'testing' | 'success' | 'error';
  }>({
    llm: 'idle',
    database: 'idle',
    service: 'idle',
  });

  const [testMessages, setTestMessages] = useState<{
    llm: string;
    database: string;
    service: string;
  }>({
    llm: '',
    database: '',
    service: '',
  });
  
  const [llmConfig, setLlmConfig] = useState<LLMConfig>({
    provider: 'openai',
    apiKey: '',
    baseUrl: 'https://api.openai.com/v1',
    model: '',
    temperature: 0.7,
    maxTokens: 4000,
  });

  const [providerConfigs, setProviderConfigs] = useState<{
    [key: string]: {
      api_key?: string;
      base_url?: string;
      endpoint?: string;
      api_version?: string;
      deployment_name?: string;
      model?: string;
      temperature?: number;
      max_tokens?: number;
    };
  }>({
    openai: { api_key: '', base_url: 'https://api.openai.com/v1', model: '', temperature: 0.7, max_tokens: 4000 },
    gpt: { api_key: '', base_url: 'https://api.openai.com/v1', model: 'gpt-4', temperature: 0.7, max_tokens: 4000 },
    anthropic: { api_key: '', base_url: 'https://api.anthropic.com', model: 'claude-3-sonnet-20240229', temperature: 0.7, max_tokens: 4000 },
    gemini: { api_key: '', base_url: 'https://generativelanguage.googleapis.com', model: 'gemini-1.5-pro', temperature: 0.7, max_tokens: 4000 },
    azure: { api_key: '', endpoint: '', api_version: '2024-02-15-preview', deployment_name: '', temperature: 0.7, max_tokens: 4000 },
    deepseek: { api_key: '', base_url: 'https://api.deepseek.com', model: 'deepseek-chat', temperature: 0.7, max_tokens: 4000 },
  });

  const [databaseConfig, setDatabaseConfig] = useState<DatabaseConfig>({
    type: 'sqlite',
    host: 'localhost',
    port: 5432,
    database: 'ai_app.db',
    username: '',
    password: '',
  });

  const [serviceConfig, setServiceConfig] = useState<ServiceConfig>({
    backendUrl: 'http://localhost:8000',
    agentUrl: 'http://localhost:8001',
    pptServiceUrl: 'http://localhost:8002',
    chartServiceUrl: 'http://localhost:8003',
    timeout: 30000,
  });

  const [appConfig, setAppConfig] = useState<AppConfig>({
    theme: 'light',
    language: 'zh-CN',
    autoSave: true,
    notifications: true,
    debugMode: false,
  });

  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [modelError, setModelError] = useState<string>('');

  useEffect(() => {
    loadConfigs();
  }, []);

  const loadConfigs = async () => {
    try {
      const configs = await configService.loadConfigs();
      const llmConfig = configs.llm as any;
      
      if (llmConfig.provider_configs) {
        const currentProvider = llmConfig.current_provider || 'openai';
        const currentProviderConfig = llmConfig.provider_configs[currentProvider] || {};
        
        const newLlmConfig = {
          provider: currentProvider,
          apiKey: currentProviderConfig.api_key || '',
          baseUrl: currentProviderConfig.base_url || currentProviderConfig.endpoint || '',
          model: currentProviderConfig.model || '',
          temperature: currentProviderConfig.temperature || 0.7,
          maxTokens: currentProviderConfig.max_tokens || 4000,
          endpoint: currentProviderConfig.endpoint || '',
          api_version: currentProviderConfig.api_version || '2024-02-15-preview',
          deployment_name: currentProviderConfig.deployment_name || '',
        };
        
        setLlmConfig(newLlmConfig);
        setProviderConfigs(llmConfig.provider_configs);
      } else {
        const provider = llmConfig.provider || 'openai';
        setLlmConfig(llmConfig);
        
        setProviderConfigs(prev => ({
          ...prev,
          [provider]: {
            ...prev[provider],
            api_key: llmConfig.apiKey || '',
            base_url: llmConfig.baseUrl || prev[provider]?.base_url || '',
            model: llmConfig.model || '',
            temperature: llmConfig.temperature || 0.7,
            max_tokens: llmConfig.maxTokens || 4000,
            ...(provider === 'azure' && {
              endpoint: llmConfig.baseUrl || llmConfig.endpoint || '',
              api_version: llmConfig.api_version || '2024-02-15-preview',
              deployment_name: llmConfig.deployment_name || llmConfig.model || '',
            }),
          }
        }));
      }
      
      setDatabaseConfig(configs.database);
      setServiceConfig(configs.service);
      setAppConfig(configs.app);
    } catch (error) {
      console.error('加载配置失败:', error);
    }
  };

  const fetchAvailableModels = async (provider: string, overrideApiKey?: string, overrideBaseUrl?: string) => {
    setLoadingModels(true);
    setModelError('');
    try {
      let apiKey = overrideApiKey || llmConfig.apiKey;
      let baseUrl = overrideBaseUrl || llmConfig.baseUrl;
      
      if (!overrideApiKey && provider !== llmConfig.provider) {
        const savedConfig = providerConfigs[provider] || {};
        apiKey = savedConfig.api_key || '';
        baseUrl = savedConfig.base_url || savedConfig.endpoint || '';
      }
      
      if (provider === 'azure') {
        baseUrl = overrideBaseUrl || llmConfig.endpoint || providerConfigs[provider]?.endpoint || '';
      }
      
      if (!apiKey) {
        setModelError('请先输入API密钥');
        setAvailableModels([]);
        return;
      }
      
      const models = await configService.getAvailableModels(provider, apiKey, baseUrl);
      
      if (models.length === 0) {
        setModelError('获取模型列表失败');
      } else {
        setModelError('');
      }
      setAvailableModels(models);
    } catch (error) {
      setModelError('获取模型列表失败');
      setAvailableModels([]);
    } finally {
      setLoadingModels(false);
    }
  };

  const handleFetchModels = () => {
    const provider = llmConfig.provider;
    const providerConfig = LLM_PROVIDERS[provider as keyof typeof LLM_PROVIDERS];
    
    if (provider && providerConfig && !providerConfig.customModel && provider !== 'azure') {
      fetchAvailableModels(provider);
    }
  };

  const saveConfigs = async () => {
    try {
      setSaveStatus('saving');
      
      const currentProvider = llmConfig.provider || 'openai';
      
      const currentProviderConfig = {
        ...providerConfigs[currentProvider] || {},
        api_key: llmConfig.apiKey,
        base_url: llmConfig.baseUrl,
        endpoint: llmConfig.endpoint,
        api_version: llmConfig.api_version,
        deployment_name: llmConfig.deployment_name,
        model: llmConfig.model,
        temperature: llmConfig.temperature,
        max_tokens: llmConfig.maxTokens,
      };

      for (const [provider, config] of Object.entries(providerConfigs)) {
        if (provider === currentProvider) {
          await configService.saveProviderConfig(provider, currentProviderConfig);
        } else if (config && Object.keys(config).some(key => config[key as keyof typeof config])) {
          await configService.saveProviderConfig(provider, config);
        }
      }

      await configService.setCurrentProvider(currentProvider);

      await configService.saveConfigs({
        llm: {
          provider: currentProvider,
          apiKey: currentProviderConfig.api_key || '',
          baseUrl: currentProviderConfig.base_url || currentProviderConfig.endpoint || '',
          model: llmConfig.model,
          temperature: llmConfig.temperature,
          maxTokens: llmConfig.maxTokens,
        },
        database: databaseConfig,
        service: serviceConfig,
        app: appConfig,
      });

      try {
        const agentUrl = serviceConfig.agentUrl || 'http://localhost:8001';
        await fetch(`${agentUrl}/api/config/llm/reload`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });
      } catch (error) {
        console.warn('无法通知Agent重新加载配置:', error);
      }

      setSaveStatus('success');
      
      setTimeout(() => {
        setSaveStatus('idle');
        navigate('/');
      }, 3000);
    } catch (error) {
      console.error('保存配置失败:', error);
      setSaveStatus('error');
      setTimeout(() => setSaveStatus('idle'), 3000);
    }
  };

  const handleGoBack = () => {
    navigate(-1);
  };

  const handleGoHome = () => {
    navigate('/');
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleProviderChange = (provider: string) => {
    const currentProvider = llmConfig.provider || 'openai';
    setProviderConfigs(prev => ({
      ...prev,
      [currentProvider]: {
        ...(prev[currentProvider] || {}),
        api_key: llmConfig.apiKey,
        base_url: llmConfig.baseUrl,
        endpoint: llmConfig.endpoint,
        api_version: llmConfig.api_version,
        deployment_name: llmConfig.deployment_name,
      }
    }));
    
    const getDefaultUrl = (provider: string) => {
      switch (provider) {
        case 'openai':
        case 'gpt':
          return 'https://api.openai.com/v1';
        case 'anthropic':
          return 'https://api.anthropic.com';
        case 'gemini':
          return 'https://generativelanguage.googleapis.com';
        case 'deepseek':
          return 'https://api.deepseek.com';
        case 'azure':
          return '';
        default:
          return '';
      }
    };

    const newProviderConfig = providerConfigs[provider] || {};
    const defaultUrl = getDefaultUrl(provider);
    
    const newConfig = {
      ...llmConfig,
      provider,
      model: newProviderConfig.model || '',
      apiKey: newProviderConfig.api_key || '',
      baseUrl: newProviderConfig.base_url || defaultUrl,
      endpoint: newProviderConfig.endpoint || (provider === 'azure' ? '' : defaultUrl),
      api_version: newProviderConfig.api_version || '2024-02-15-preview',
      deployment_name: newProviderConfig.deployment_name || '',
      temperature: newProviderConfig.temperature || 0.7,
      maxTokens: newProviderConfig.max_tokens || 4000,
    };
    
    setLlmConfig(newConfig);
    setAvailableModels([]);
    setModelError('');
    
    setTimeout(() => {
      const providerConfig = LLM_PROVIDERS[provider as keyof typeof LLM_PROVIDERS];
      
      if (newProviderConfig.api_key && 
          providerConfig && 
          !providerConfig.customModel && 
          provider !== 'azure') {
        const baseUrl = newProviderConfig.base_url || defaultUrl;
        fetchAvailableModels(provider, newProviderConfig.api_key, baseUrl);
      }
    }, 100);
  };

  const testConnection = async (type: 'llm' | 'database' | 'service') => {
    try {
      setTestStatus(prev => ({ ...prev, [type]: 'testing' }));
      setTestMessages(prev => ({ ...prev, [type]: '正在测试连接...' }));
      
      let currentConfig: LLMConfig | DatabaseConfig | ServiceConfig;
      switch (type) {
        case 'llm':
          const provider = llmConfig.provider;
          let baseUrl = llmConfig.baseUrl;
          
          if (provider === 'azure') {
            baseUrl = llmConfig.endpoint || '';
          }
          
          currentConfig = {
            provider: llmConfig.provider || 'openai',
            apiKey: llmConfig.apiKey || '',
            baseUrl: baseUrl,
            model: llmConfig.model || '',
            temperature: llmConfig.temperature || 0.7,
            maxTokens: llmConfig.maxTokens || 4000,
            ...(provider === 'azure' && {
              endpoint: llmConfig.endpoint,
              api_version: llmConfig.api_version,
              deployment_name: llmConfig.deployment_name,
            })
          };
          break;
        case 'database':
          currentConfig = databaseConfig;
          break;
        case 'service':
          currentConfig = serviceConfig;
          break;
        default:
          throw new Error(`未知的配置类型: ${type}`);
      }
      
      const result = await configService.testConnection(type, currentConfig);
      
      if (result) {
        setTestStatus(prev => ({ ...prev, [type]: 'success' }));
        const successMessage = type === 'llm' && 'model' in currentConfig 
          ? `${(currentConfig.provider || 'Unknown').toUpperCase()} - 模型 "${currentConfig.model || 'Unknown'}" 验证成功` 
          : '连接测试成功';
        setTestMessages(prev => ({ 
          ...prev, 
          [type]: successMessage
        }));
      } else {
        setTestStatus(prev => ({ ...prev, [type]: 'error' }));
        const errorMessage = type === 'llm' && 'model' in currentConfig 
          ? `${(currentConfig.provider || 'Unknown').toUpperCase()} - 模型 "${currentConfig.model || 'Unknown'}" 验证失败` 
          : '连接测试失败';
        setTestMessages(prev => ({ 
          ...prev, 
          [type]: errorMessage
        }));
      }
      
      setTimeout(() => {
        setTestStatus(prev => ({ ...prev, [type]: 'idle' }));
        setTestMessages(prev => ({ ...prev, [type]: '' }));
      }, 5000);
      
      return result;
    } catch (error) {
      setTestStatus(prev => ({ ...prev, [type]: 'error' }));
      setTestMessages(prev => ({ ...prev, [type]: '测试过程中发生错误' }));
      
      setTimeout(() => {
        setTestStatus(prev => ({ ...prev, [type]: 'idle' }));
        setTestMessages(prev => ({ ...prev, [type]: '' }));
      }, 5000);
      
      return false;
    }
  };

  const exportConfigs = async () => {
    try {
      const configJson = await configService.exportConfigs();
      const blob = new Blob([configJson], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'ai-app-configs.json';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('导出配置失败:', error);
    }
  };

  const importConfigs = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      await configService.importConfigs(text);
      await loadConfigs();
      setSaveStatus('success');
      setTimeout(() => setSaveStatus('idle'), 3000);
    } catch (error) {
      console.error('导入配置失败:', error);
      setSaveStatus('error');
      setTimeout(() => setSaveStatus('idle'), 3000);
    }
  };

  const resetConfigs = async () => {
    if (window.confirm('确定要重置所有配置到默认值吗？此操作不可撤销。')) {
      try {
        await configService.resetConfigs();
        await loadConfigs();
        setSaveStatus('success');
        setTimeout(() => setSaveStatus('idle'), 3000);
      } catch (error) {
        console.error('重置配置失败:', error);
        setSaveStatus('error');
        setTimeout(() => setSaveStatus('idle'), 3000);
      }
    }
  };

  const renderTestStatus = (type: 'llm' | 'database' | 'service') => {
    const status = testStatus[type];
    const message = testMessages[type];
    
    switch (status) {
      case 'testing':
        return <Chip label={message || "测试中..."} color="info" />;
      case 'success':
        return <Chip label={message || "连接成功"} color="success" icon={<CheckIcon />} />;
      case 'error':
        return <Chip label={message || "连接失败"} color="error" />;
      default:
        return <Chip label="未测试" color="default" />;
    }
  };

  const renderProviderFields = () => {
    const provider = llmConfig.provider || 'openai';
    const providerConfig = LLM_PROVIDERS[provider as keyof typeof LLM_PROVIDERS];
    
    if (!providerConfig) return null;

    const updateProviderConfig = (field: string, value: string) => {
      setLlmConfig(prev => ({ ...prev, [field]: value }));
      
      const fieldMapping: { [key: string]: string } = {
        'apiKey': 'api_key',
        'baseUrl': 'base_url',
        'endpoint': 'endpoint',
        'api_version': 'api_version',
        'deployment_name': 'deployment_name'
      };
      
      const backendField = fieldMapping[field] || field;
      
      setProviderConfigs(prev => ({
        ...prev,
        [provider]: {
          ...(prev[provider] || {}),
          [backendField]: value
        }
      }));
    };

    return (
      <>
        {providerConfig.fields.includes('api_key') && (
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="API 密钥"
              type={showPasswords ? 'text' : 'password'}
              value={llmConfig.apiKey}
              onChange={(e) => updateProviderConfig('apiKey', e.target.value)}
              InputProps={{
                endAdornment: (
                  <IconButton
                    onClick={() => setShowPasswords(!showPasswords)}
                    edge="end"
                  >
                    {showPasswords ? <VisibilityOffIcon /> : <VisibilityIcon />}
                  </IconButton>
                ),
              }}
            />
          </Grid>
        )}

        {providerConfig.fields.includes('base_url') && (
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="API 基础 URL"
              value={llmConfig.baseUrl}
              onChange={(e) => updateProviderConfig('baseUrl', e.target.value)}
            />
          </Grid>
        )}

        {provider === 'azure' && (
          <>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Azure 端点"
                value={llmConfig.endpoint}
                onChange={(e) => updateProviderConfig('endpoint', e.target.value)}
                placeholder="https://your-resource.openai.azure.com/"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="API 版本"
                value={llmConfig.api_version}
                onChange={(e) => updateProviderConfig('api_version', e.target.value)}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="部署名称"
                value={llmConfig.deployment_name}
                onChange={(e) => updateProviderConfig('deployment_name', e.target.value)}
                placeholder="gpt-4"
              />
            </Grid>
          </>
        )}

        {providerConfig.fields.includes('model') && (
          <Grid item xs={12} md={6}>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
              <Box sx={{ flexGrow: 1 }}>
                {providerConfig.customModel ? (
                  <TextField
                    fullWidth
                    label="模型名称"
                    value={llmConfig.model}
                    onChange={(e) => setLlmConfig({ ...llmConfig, model: e.target.value })}
                    placeholder="输入模型名称"
                  />
                ) : provider === 'azure' ? (
                  <TextField
                    fullWidth
                    label="部署名称"
                    value={llmConfig.model}
                    onChange={(e) => setLlmConfig({ ...llmConfig, model: e.target.value })}
                    placeholder="输入部署名称"
                  />
                ) : (
                  <Autocomplete
                    fullWidth
                    options={availableModels}
                    value={llmConfig.model}
                    onChange={(event, newValue) => {
                      setLlmConfig({ ...llmConfig, model: newValue || '' });
                    }}
                    loading={loadingModels}
                    freeSolo={true}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        label="模型名称"
                        placeholder="选择或输入模型名称"
                        error={!!modelError}
                        helperText={loadingModels ? "正在加载模型列表..." : 
                                   modelError ? modelError :
                                   availableModels.length === 0 ? "点击获取按钮加载模型列表" : `已加载 ${availableModels.length} 个模型`}
                      />
                    )}
                  />
                )}
              </Box>
              
              {!providerConfig.customModel && provider !== 'azure' && (
                <IconButton
                  onClick={handleFetchModels}
                  disabled={loadingModels || !llmConfig.apiKey}
                  sx={{ 
                    height: '56px',
                    width: '56px',
                    border: '1px solid',
                    borderColor: 'divider',
                    borderRadius: 1,
                  }}
                  title={loadingModels ? '获取中...' : '获取模型列表'}
                >
                  <RefreshIcon 
                    sx={{ 
                      animation: loadingModels ? 'spin 1s linear infinite' : 'none',
                      '@keyframes spin': {
                        '0%': { transform: 'rotate(0deg)' },
                        '100%': { transform: 'rotate(360deg)' },
                      }
                    }} 
                  />
                </IconButton>
              )}
            </Box>
          </Grid>
        )}

        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="温度 (Temperature)"
            type="number"
            value={llmConfig.temperature}
            onChange={(e) => setLlmConfig({ ...llmConfig, temperature: parseFloat(e.target.value) })}
            inputProps={{ min: 0, max: 2, step: 0.1 }}
          />
        </Grid>

        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="最大令牌数"
            type="number"
            value={llmConfig.maxTokens}
            onChange={(e) => setLlmConfig({ ...llmConfig, maxTokens: parseInt(e.target.value) })}
            inputProps={{ min: 1, max: 32768 }}
          />
        </Grid>
      </>
    );
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<BackIcon />}
            onClick={handleGoBack}
            size="small"
          >
            返回
          </Button>
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
              ⚙️ 系统设置
            </Typography>
            <Typography variant="body1" color="text.secondary">
              配置应用的各项参数和连接信息
            </Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <input
            type="file"
            accept=".json"
            style={{ display: 'none' }}
            id="import-config"
            onChange={importConfigs}
          />
          <label htmlFor="import-config">
            <Button
              variant="outlined"
              component="span"
              startIcon={<ImportIcon />}
              size="small"
            >
              导入
            </Button>
          </label>
          <Button
            variant="outlined"
            startIcon={<ExportIcon />}
            onClick={exportConfigs}
            size="small"
          >
            导出
          </Button>
          <Button
            variant="outlined"
            startIcon={<ResetIcon />}
            onClick={resetConfigs}
            size="small"
            color="warning"
          >
            重置
          </Button>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadConfigs}
          >
            重新加载
          </Button>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={saveConfigs}
            disabled={saveStatus === 'saving'}
          >
            {saveStatus === 'saving' ? '保存中...' : '保存配置'}
          </Button>
        </Box>
      </Box>

      {saveStatus === 'success' && (
        <Alert severity="success" sx={{ mb: 2 }} icon={<CheckIcon />}>
          配置保存成功！3秒后自动返回仪表板...
          <Button
            size="small"
            onClick={handleGoHome}
            sx={{ ml: 2 }}
          >
            立即返回
          </Button>
        </Alert>
      )}

      {saveStatus === 'error' && (
        <Alert severity="error" sx={{ mb: 2 }}>
          配置保存失败，请重试。
        </Alert>
      )}

      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab label="LLM 配置" />
            <Tab label="数据库配置" />
            <Tab label="服务配置" />
            <Tab label="应用设置" />
          </Tabs>
        </Box>

        <TabPanel value={tabValue} index={0}>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <InfoIcon color="primary" />
              大语言模型配置
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              配置用于 AI 功能的大语言模型服务
            </Typography>

            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>服务提供商</InputLabel>
                  <Select
                    value={llmConfig.provider}
                    label="服务提供商"
                    onChange={(e) => handleProviderChange(e.target.value)}
                  >
                    {Object.entries(LLM_PROVIDERS).map(([key, config]) => (
                      <MenuItem key={key} value={key}>
                        <Box>
                          <Typography variant="body1">{config.name}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            {config.description}
                          </Typography>
                        </Box>
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              {renderProviderFields()}

              <Grid item xs={12}>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Button
                      variant="outlined"
                      onClick={() => testConnection('llm')}
                      disabled={
                        testStatus.llm === 'testing' || 
                        !llmConfig.apiKey || 
                        !llmConfig.model
                      }
                      sx={{ minWidth: '100px' }}
                    >
                      {testStatus.llm === 'testing' ? '测试中...' : '测试连接'}
                    </Button>
                    {renderTestStatus('llm')}
                  </Box>
                  {(!llmConfig.apiKey || !llmConfig.model) && (
                    <Typography variant="caption" color="text.secondary">
                      {!llmConfig.apiKey ? '请先输入API密钥' : '请先选择或输入模型名称'}
                    </Typography>
                  )}
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <InfoIcon color="primary" />
              数据库配置
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              配置应用数据存储
            </Typography>

            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>数据库类型</InputLabel>
                  <Select
                    value={databaseConfig.type}
                    label="数据库类型"
                    onChange={(e) => setDatabaseConfig({ ...databaseConfig, type: e.target.value })}
                  >
                    <MenuItem value="sqlite">SQLite</MenuItem>
                    <MenuItem value="postgresql">PostgreSQL</MenuItem>
                    <MenuItem value="mysql">MySQL</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="数据库名称"
                  value={databaseConfig.database}
                  onChange={(e) => setDatabaseConfig({ ...databaseConfig, database: e.target.value })}
                />
              </Grid>

              {databaseConfig.type !== 'sqlite' && (
                <>
                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="主机地址"
                      value={databaseConfig.host}
                      onChange={(e) => setDatabaseConfig({ ...databaseConfig, host: e.target.value })}
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="端口"
                      type="number"
                      value={databaseConfig.port}
                      onChange={(e) => setDatabaseConfig({ ...databaseConfig, port: parseInt(e.target.value) })}
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="用户名"
                      value={databaseConfig.username}
                      onChange={(e) => setDatabaseConfig({ ...databaseConfig, username: e.target.value })}
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="密码"
                      type={showPasswords ? 'text' : 'password'}
                      value={databaseConfig.password}
                      onChange={(e) => setDatabaseConfig({ ...databaseConfig, password: e.target.value })}
                      InputProps={{
                        endAdornment: (
                          <IconButton
                            onClick={() => setShowPasswords(!showPasswords)}
                            edge="end"
                          >
                            {showPasswords ? <VisibilityOffIcon /> : <VisibilityIcon />}
                          </IconButton>
                        ),
                      }}
                    />
                  </Grid>
                </>
              )}

              <Grid item xs={12}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Button
                  variant="outlined"
                  onClick={() => testConnection('database')}
                  disabled={testStatus.database === 'testing'}
                    sx={{ minWidth: '100px' }}
                >
                  {testStatus.database === 'testing' ? '测试中...' : '测试连接'}
                </Button>
                {renderTestStatus('database')}
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <InfoIcon color="primary" />
              服务配置
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              配置各个微服务的连接地址
            </Typography>

            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="后端服务 URL"
                  value={serviceConfig.backendUrl}
                  onChange={(e) => setServiceConfig({ ...serviceConfig, backendUrl: e.target.value })}
                  placeholder="http://localhost:8000"
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="AI Agent URL"
                  value={serviceConfig.agentUrl}
                  onChange={(e) => setServiceConfig({ ...serviceConfig, agentUrl: e.target.value })}
                  placeholder="http://localhost:8080"
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="PPT 生成服务 URL"
                  value={serviceConfig.pptServiceUrl}
                  onChange={(e) => setServiceConfig({ ...serviceConfig, pptServiceUrl: e.target.value })}
                  placeholder="http://localhost:8002"
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="图表生成服务 URL"
                  value={serviceConfig.chartServiceUrl}
                  onChange={(e) => setServiceConfig({ ...serviceConfig, chartServiceUrl: e.target.value })}
                  placeholder="http://localhost:8003"
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="请求超时时间 (毫秒)"
                  type="number"
                  value={serviceConfig.timeout}
                  onChange={(e) => setServiceConfig({ ...serviceConfig, timeout: parseInt(e.target.value) })}
                  inputProps={{ min: 1000, max: 300000 }}
                />
              </Grid>

              <Grid item xs={12}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Button
                  variant="outlined"
                  onClick={() => testConnection('service')}
                  disabled={testStatus.service === 'testing'}
                    sx={{ minWidth: '120px' }}
                >
                  {testStatus.service === 'testing' ? '测试中...' : '测试所有服务'}
                </Button>
                {renderTestStatus('service')}
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <InfoIcon color="primary" />
              应用设置
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              配置应用的外观和行为
            </Typography>

            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>主题</InputLabel>
                  <Select
                    value={appConfig.theme}
                    label="主题"
                    onChange={(e) => setAppConfig({ ...appConfig, theme: e.target.value })}
                  >
                    <MenuItem value="light">浅色主题</MenuItem>
                    <MenuItem value="dark">深色主题</MenuItem>
                    <MenuItem value="auto">跟随系统</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>语言</InputLabel>
                  <Select
                    value={appConfig.language}
                    label="语言"
                    onChange={(e) => setAppConfig({ ...appConfig, language: e.target.value })}
                  >
                    <MenuItem value="zh-CN">简体中文</MenuItem>
                    <MenuItem value="en-US">English</MenuItem>
                    <MenuItem value="ja-JP">日本語</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12}>
                <Divider sx={{ my: 2 }} />
                <Typography variant="subtitle1" gutterBottom>
                  功能设置
                </Typography>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={appConfig.autoSave}
                      onChange={(e) => setAppConfig({ ...appConfig, autoSave: e.target.checked })}
                    />
                  }
                  label="自动保存"
                />
                <Typography variant="body2" color="text.secondary">
                  自动保存用户输入和配置
                </Typography>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={appConfig.notifications}
                      onChange={(e) => setAppConfig({ ...appConfig, notifications: e.target.checked })}
                    />
                  }
                  label="桌面通知"
                />
                <Typography variant="body2" color="text.secondary">
                  任务完成时显示桌面通知
                </Typography>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={appConfig.debugMode}
                      onChange={(e) => setAppConfig({ ...appConfig, debugMode: e.target.checked })}
                    />
                  }
                  label="调试模式"
                />
                <Typography variant="body2" color="text.secondary">
                  显示详细的调试信息
                </Typography>
              </Grid>
            </Grid>
          </CardContent>
        </TabPanel>
      </Card>
    </Box>
  );
};

export default Settings; 