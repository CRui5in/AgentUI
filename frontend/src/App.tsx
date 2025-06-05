import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Box, AppBar, Toolbar, Typography, Container, ThemeProvider, CssBaseline } from '@mui/material';
import Dashboard from './components/Dashboard';
import TaskManager from './components/TaskManager';
import PPTGenerator from './components/PPTGenerator';
import ChartGenerator from './components/ChartGenerator';
import ScheduleManager from './components/ScheduleManager';
import APIDocGenerator from './components/APIDocGenerator';
import Navigation from './components/Navigation';
import Settings from './components/Settings';
import theme from './theme';

/**
 * 主应用组件
 * 包含应用的主要布局、路由配置和导航
 */
function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ flexGrow: 1, minHeight: '100vh', backgroundColor: 'background.default' }}>
        {/* 顶部应用栏 */}
        <AppBar position="static" elevation={0}>
          <Toolbar sx={{ px: 3 }}>
            <Typography variant="h5" component="div" sx={{ flexGrow: 1, fontWeight: 600 }}>
              🚀 AgentUI
            </Typography>
            <Typography variant="body2" color="text.secondary">
              AgentUI
            </Typography>
          </Toolbar>
        </AppBar>

        {/* 主要内容区域 */}
        <Container maxWidth="xl" sx={{ py: 4 }}>
          <Box sx={{ display: 'flex', gap: 4 }}>
            {/* 侧边导航 */}
            <Box sx={{ width: 280, flexShrink: 0 }}>
              <Navigation />
            </Box>

            {/* 主内容区 */}
            <Box sx={{ flexGrow: 1, minWidth: 0 }}>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/tasks" element={<TaskManager />} />
                <Route path="/ppt-generator" element={<PPTGenerator />} />
                <Route path="/chart-generator" element={<ChartGenerator />} />
                <Route path="/scheduler" element={<ScheduleManager />} />
                <Route path="/api-docs" element={<APIDocGenerator />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </Box>
          </Box>
        </Container>
      </Box>
    </ThemeProvider>
  );
}

export default App; 