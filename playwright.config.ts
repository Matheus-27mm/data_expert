import {defineConfig} from '@playwright/test';
export default defineConfig({
 testDir:'./tests/browser',fullyParallel:false,workers:1,timeout:30000,
 use:{baseURL:'http://127.0.0.1:5174',trace:'retain-on-failure'},
 reporter:[['list'],['html',{open:'never'}]],
 webServer:[
  {command:'python -m uvicorn tests.e2e_api:app --host 127.0.0.1 --port 8011',url:'http://127.0.0.1:8011/api/health',reuseExistingServer:false},
  {command:'npm run dev -- --port 5174 --strictPort',url:'http://127.0.0.1:5174',env:{API_PROXY_TARGET:'http://127.0.0.1:8011'},reuseExistingServer:false}
 ]
});
