import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
// Third-party code in its own long-lived chunks: app deploys stop invalidating
// the browser cache for React and the auth SDK.
export default defineConfig({plugins:[react()],server:{proxy:{'/api':process.env.API_PROXY_TARGET||'http://127.0.0.1:8000'}},
 build:{rollupOptions:{output:{manualChunks(id){if(!id.includes('node_modules'))return;if(/[\/](react|react-dom|scheduler)[\/]/.test(id))return 'react';if(id.includes('lucide-react'))return 'icons';return 'vendor'}}}}});
