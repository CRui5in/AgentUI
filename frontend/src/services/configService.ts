/**
 * 配置服务
 * 管理应用的各种配置信息
 */

export interface LLMConfig {
  provider?: string;
  apiKey?: string;
  baseUrl?: string;
  model?: string;
  temperature?: number;
  maxTokens?: number;
  endpoint?: string;
  api_version?: string;
  deployment_name?: string;
  current_provider?: string;
  provider_configs?: {
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
  };
}

export interface DatabaseConfig {
  type: string;
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
}

export interface ServiceConfig {
  backendUrl: string;
  agentUrl: string;
  pptServiceUrl: string;
  chartServiceUrl: string;
  timeout: number;
}

export interface AppConfig {
  theme: string;
  language: string;
  autoSave: boolean;
  notifications: boolean;
  debugMode: boolean;
}

export interface AppConfigs {
  llm: LLMConfig;
  database: DatabaseConfig;
  service: ServiceConfig;
  app: AppConfig;
}

class ConfigService {
  private readonly STORAGE_KEY = 'aiAppConfigs';
  private readonly API_BASE_URL = 'http://localhost:8000/api';

  private getDefaultConfigs(): AppConfigs {
    return {
      llm: {
        provider: 'openai',
        apiKey: '',
        baseUrl: 'https://api.openai.com/v1',
        model: '',
        temperature: 0.7,
        maxTokens: 2048,
      },
      database: {
        type: 'sqlite',
        host: 'localhost',
        port: 5432,
        database: 'ai_app.db',
        username: '',
        password: '',
      },
      service: {
        backendUrl: 'http://localhost:8000',
        agentUrl: 'http://localhost:8001',
        pptServiceUrl: 'http://localhost:8002',
        chartServiceUrl: 'http://localhost:8003',
        timeout: 30000,
      },
      app: {
        theme: 'light',
        language: 'zh-CN',
        autoSave: true,
        notifications: true,
        debugMode: false,
      },
    };
  }

  async loadConfigs(): Promise<AppConfigs> {
    try {
      const response = await fetch(`${this.API_BASE_URL}/settings/all`);
      if (response.ok) {
        const configs = await response.json();
        
        const frontendConfigs = {
          llm: configs.llm,
          database: {
            type: configs.database.type,
            host: configs.database.host,
            port: configs.database.port,
            database: configs.database.database,
            username: configs.database.username,
            password: configs.database.password,
          },
          service: {
            backendUrl: configs.service.backend_url,
            agentUrl: configs.service.agent_url,
            pptServiceUrl: configs.service.ppt_service_url,
            chartServiceUrl: configs.service.chart_service_url,
            timeout: configs.service.timeout,
          },
          app: {
            theme: configs.app.theme,
            language: configs.app.language,
            autoSave: configs.app.auto_save,
            notifications: configs.app.notifications,
            debugMode: configs.app.debug_mode,
          }
        };
        
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(frontendConfigs));
        return this.mergeConfigs(this.getDefaultConfigs(), frontendConfigs);
      }
    } catch (error) {
      console.warn('从后端API加载配置失败，尝试本地存储:', error);
    }
    
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      if (stored) {
        const configs = JSON.parse(stored);
        return this.mergeConfigs(this.getDefaultConfigs(), configs);
      }
    } catch (error) {
      console.error('加载本地配置失败:', error);
    }
    
    return this.getDefaultConfigs();
  }

  async saveConfigs(configs: AppConfigs): Promise<void> {
    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(configs));
    
    const backendConfigs = {
      llm: {
        provider: configs.llm.provider,
        api_key: configs.llm.apiKey,
        base_url: configs.llm.baseUrl,
        model: configs.llm.model,
        temperature: configs.llm.temperature,
        max_tokens: configs.llm.maxTokens,
      },
      database: {
        type: configs.database.type,
        host: configs.database.host,
        port: configs.database.port,
        database: configs.database.database,
        username: configs.database.username,
        password: configs.database.password,
      },
      service: {
        backend_url: configs.service.backendUrl,
        agent_url: configs.service.agentUrl,
        ppt_service_url: configs.service.pptServiceUrl,
        chart_service_url: configs.service.chartServiceUrl,
        timeout: configs.service.timeout,
      },
      app: {
        theme: configs.app.theme,
        language: configs.app.language,
        auto_save: configs.app.autoSave,
        notifications: configs.app.notifications,
        debug_mode: configs.app.debugMode,
      }
    };
    
    const response = await fetch(`${this.API_BASE_URL}/settings/all`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(backendConfigs),
    });
    
    if (!response.ok) {
      throw new Error(`保存到后端失败: ${response.status} ${response.statusText}`);
    }
  }

  async getConfig<T extends keyof AppConfigs>(type: T): Promise<AppConfigs[T]> {
    const configs = await this.loadConfigs();
    return configs[type];
  }

  async updateConfig<T extends keyof AppConfigs>(
    type: T,
    config: Partial<AppConfigs[T]>
  ): Promise<void> {
    const configs = await this.loadConfigs();
    configs[type] = { ...configs[type], ...config };
    await this.saveConfigs(configs);
  }

  async testConnection(type: 'llm' | 'database' | 'service', config?: any): Promise<boolean> {
    try {
      const testConfig = config || await this.getConfig(type);
      
      switch (type) {
        case 'llm':
          return await this.testLLMConnection(testConfig as LLMConfig);
        case 'database':
          return await this.testDatabaseConnection(testConfig as DatabaseConfig);
        case 'service':
          return await this.testServiceConnection(testConfig as ServiceConfig);
        default:
          return false;
      }
    } catch (error) {
      console.error(`测试 ${type} 连接失败:`, error);
      return false;
    }
  }

  private async testLLMConnection(config: LLMConfig): Promise<boolean> {
    try {
      if (!config.apiKey || config.apiKey.trim() === '') {
        return false;
      }
      
      const testConfig = {
        provider: config.provider,
        api_key: config.apiKey,
        base_url: config.baseUrl,
        model: config.model,
        temperature: config.temperature,
        max_tokens: config.maxTokens,
        ...(config.provider === 'azure' && {
          endpoint: config.endpoint,
          api_version: config.api_version,
          deployment_name: config.deployment_name,
        })
      };
      
      const response = await fetch(`${this.API_BASE_URL}/settings/test/llm`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(testConfig),
        signal: AbortSignal.timeout(30000)
      });
      
      if (response.ok) {
        const result = await response.json();
        return result.success;
      }
      return false;
    } catch (error) {
      return false;
    }
  }

  private async testDatabaseConnection(config: DatabaseConfig): Promise<boolean> {
    try {
      if (!config.database || config.database.trim() === '') {
        return false;
      }
      
      if (config.type !== 'sqlite') {
        if (!config.host || config.host.trim() === '' || !config.port || config.port <= 0) {
          return false;
        }
      }
      
      const serviceConfig = await this.getConfig('service');
      
      const response = await fetch(`${serviceConfig.backendUrl}/api/test/database`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
        signal: AbortSignal.timeout(10000)
      });
      
      return response.ok;
    } catch (error) {
      return false;
    }
  }

  private async testServiceConnection(config: ServiceConfig): Promise<boolean> {
    try {
      const services = [
        { name: 'Backend', url: config.backendUrl },
        { name: 'Agent', url: config.agentUrl },
        { name: 'PPT Service', url: config.pptServiceUrl },
        { name: 'Chart Service', url: config.chartServiceUrl },
      ];
      
      const results = await Promise.allSettled(
        services.map(async service => {
          try {
            const response = await fetch(`${service.url}/api/system/health/`, { 
              method: 'GET',
              signal: AbortSignal.timeout(5000)
            });
            
            if (response.ok) {
              return { service: service.name, success: true, response };
            }
          } catch (healthError) {
            // 尝试备用端点
          }
          
          try {
            const response = await fetch(`${service.url}/health`, { 
              method: 'GET',
              signal: AbortSignal.timeout(5000)
            });
            
            if (response.ok) {
              return { service: service.name, success: true, response };
            }
          } catch (backupError) {
            // 忽略错误
          }
          
          throw new Error(`${service.name} 所有端点都无法连接`);
        })
      );

      const successfulServices = results.filter(result => 
        result.status === 'fulfilled' && result.value.success
      );
      
      const successCount = successfulServices.length;
      
      if (successCount === 0) {
        return false;
      }
      
      return successCount >= Math.ceil(services.length / 2);
    } catch (error) {
      return false;
    }
  }

  private mergeConfigs(defaults: AppConfigs, stored: Partial<AppConfigs>): AppConfigs {
    return {
      llm: { ...defaults.llm, ...stored.llm },
      database: { ...defaults.database, ...stored.database },
      service: { ...defaults.service, ...stored.service },
      app: { ...defaults.app, ...stored.app },
    };
  }

  async resetConfigs(): Promise<void> {
    const defaults = this.getDefaultConfigs();
    await this.saveConfigs(defaults);
  }

  async exportConfigs(): Promise<string> {
    const configs = await this.loadConfigs();
    return JSON.stringify(configs, null, 2);
  }

  async importConfigs(configJson: string): Promise<void> {
    try {
      const configs = JSON.parse(configJson);
      const mergedConfigs = this.mergeConfigs(this.getDefaultConfigs(), configs);
      await this.saveConfigs(mergedConfigs);
    } catch (error) {
      throw new Error('配置格式无效');
    }
  }

  async getAvailableModels(provider: string, apiKey?: string, baseUrl?: string): Promise<string[]> {
    try {
      const params = new URLSearchParams();
      if (apiKey) params.append('api_key', apiKey);
      if (baseUrl) params.append('base_url', baseUrl);
      
      const url = `${this.API_BASE_URL}/settings/llm/models/${provider}${params.toString() ? '?' + params.toString() : ''}`;
      
      const response = await fetch(url);
      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          return result.models || [];
        }
      }
      return [];
    } catch (error) {
      return [];
    }
  }

  async saveProviderConfig(provider: string, config: any): Promise<void> {
    const response = await fetch(`${this.API_BASE_URL}/settings/llm/provider/${provider}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(config),
    });

    if (!response.ok) {
      throw new Error(`保存提供商 ${provider} 配置失败: ${response.status}`);
    }
  }

  async setCurrentProvider(provider: string): Promise<void> {
    const response = await fetch(`${this.API_BASE_URL}/settings/llm/current/${provider}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`设置当前提供商失败: ${response.status}`);
    }
  }
}

export const configService = new ConfigService();
export default configService; 