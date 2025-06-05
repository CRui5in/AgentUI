import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Paper,
  Divider,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Assignment as TaskIcon,
  Slideshow as PptIcon,
  BarChart as ChartIcon,
  Schedule as ScheduleIcon,
  Description as DocsIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';

/**
 * 导航菜单项接口
 */
interface NavigationItem {
  path: string;
  label: string;
  icon: React.ReactElement;
}

/**
 * 侧边导航组件
 * 提供应用的主要导航功能
 */
const Navigation: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  // 导航菜单项配置
  const navigationItems: NavigationItem[] = [
    {
      path: '/',
      label: '仪表板',
      icon: <DashboardIcon />,
    },
    {
      path: '/tasks',
      label: '任务管理',
      icon: <TaskIcon />,
    },
  ];

  // 工具服务菜单项
  const toolItems: NavigationItem[] = [
    {
      path: '/ppt-generator',
      label: 'PPT 生成器',
      icon: <PptIcon />,
    },
    {
      path: '/chart-generator',
      label: '图表生成器',
      icon: <ChartIcon />,
    },
    {
      path: '/scheduler',
      label: '日程管理',
      icon: <ScheduleIcon />,
    },
    {
      path: '/api-docs',
      label: 'API 文档',
      icon: <DocsIcon />,
    },
  ];

  /**
   * 处理导航点击事件
   */
  const handleNavigation = (path: string) => {
    navigate(path);
  };

  /**
   * 检查当前路径是否激活
   */
  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <Paper elevation={0} sx={{ height: 'fit-content', border: '1px solid', borderColor: 'divider' }}>
      <List component="nav" sx={{ p: 1 }}>
        {/* 主要导航项 */}
        {navigationItems.map((item) => (
          <ListItem key={item.path} disablePadding>
            <ListItemButton
              selected={isActive(item.path)}
              onClick={() => handleNavigation(item.path)}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          </ListItem>
        ))}

        <Divider sx={{ my: 2 }} />

        {/* 工具服务导航项 */}
        {toolItems.map((item) => (
          <ListItem key={item.path} disablePadding>
            <ListItemButton
              selected={isActive(item.path)}
              onClick={() => handleNavigation(item.path)}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          </ListItem>
        ))}

        <Divider sx={{ my: 2 }} />

        {/* 系统设置 */}
        <ListItem disablePadding>
          <ListItemButton
            selected={isActive('/settings')}
            onClick={() => handleNavigation('/settings')}
          >
            <ListItemIcon>
              <SettingsIcon />
            </ListItemIcon>
            <ListItemText primary="系统设置" />
          </ListItemButton>
        </ListItem>
      </List>
    </Paper>
  );
};

export default Navigation; 