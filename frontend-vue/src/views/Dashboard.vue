> <script lang="ts">
export default { name: 'Dashboard' }
</script>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import BboxImage from '../components/BboxImage.vue'

const router = useRouter()

// 状态
const cameras = ref<any[]>([]) // 动态加载的摄像头列表（支持4个及以上）
const selectedCameraId = ref<number | null>(null)
const logs = ref<string[]>([])
const alerts = ref<any[]>([])
const latestAlert = computed(() => alerts.value.length > 0 ? alerts.value[0] : null)

// 当前选中摄像头的流地址 (主画面展示)
// 当前选中摄像头的流地址 (主画面展示)
const selectedCameraStreamUrl = computed(() => {
  const selected = cameras.value.find(c => c.id === selectedCameraId.value)
  return selected ? `http://127.0.0.1:8000/api/video_feed/${selected.id}` : null
})

let ws: WebSocket | null = null;

onMounted(async () => {
  // 定义后端基础地址，动态获取当前 IP，避免跨域报错
  const backendBaseUrl = `http://${window.location.hostname}:8000`

  // 1. 获取摄像头列表
  try {
    const response = await fetch(`${backendBaseUrl}/api/config/cameras`)
    const data = await response.json()
    cameras.value = data
    if (cameras.value.length > 0) {
      selectedCameraId.value = cameras.value[0].id 
    }
    logs.value.push(`[${new Date().toLocaleTimeString()}] ✅ 成功加载 ${cameras.value.length} 路视频源`)
  } catch (error) {
    logs.value.push(`[${new Date().toLocaleTimeString()}] ❌ 获取视频源失败`)
  }

  // 👇 【新增】：2. 加载历史告警记录
  try {
    const historyRes = await fetch(`${backendBaseUrl}/api/alerts/history?limit=20`) // 默认拉取最近20条
    const historyData = await historyRes.json()
    
    // 将数据存入 alerts 列表。注意要将 /static/... 拼接为完整 HTTP 路径

    alerts.value = historyData.map((item: any) => {
    // 兼容前端所需字段与后端模型字段
    const imgUrl = item.image_url || item.img || '';
    return {
        ...item,
        id: item.id,
        type: item.issue_type || item.type,
        time: item.created_at || item.time,
        camera: item.camera_name || item.camera,
        desc: item.issue_description || item.desc,
        img: imgUrl.startsWith('http') ? imgUrl : `${backendBaseUrl}${imgUrl}`
    }
    })
    
    if (historyData.length > 0) {
      logs.value.push(`[${new Date().toLocaleTimeString()}] 💾 成功从数据库加载 ${historyData.length} 条历史抓拍记录`)
    }
  } catch (error) {
    console.error('获取历史记录失败:', error)
    logs.value.push(`[${new Date().toLocaleTimeString()}] ⚠️ 历史记录加载失败`)
  }

  // 3. 连接 WebSocket (大模型实时告警)
  const wsUrl = `ws://${window.location.hostname}:8000/ws/alerts`
  ws = new WebSocket(wsUrl)
  
  ws.onopen = () => logs.value.push(`[${new Date().toLocaleTimeString()}] 🔗 成功连接 AI 实时告警通道`)
  ws.onclose = () => logs.value.push(`[${new Date().toLocaleTimeString()}] ❌ AI 告警通道已断开`)
  ws.onerror = (error) => logs.value.push(`[${new Date().toLocaleTimeString()}] ⚠️ 告警通道发生网络错误`)

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'info') {
      logs.value.push(`[${new Date().toLocaleTimeString()}] ${data.message}`)
    } else if (data.type === 'alert') {
      logs.value.push(`[${new Date().toLocaleTimeString()}] 🚨 收到新告警: ${data.alert.type}`)
      
      // 收到实时告警时，也要判断一下图片路径（实时发来的可能还是 base64，历史的是 url）
      alerts.value.unshift(data.alert)
    }
  }
})

onUnmounted(() => { if (ws) ws.close() })

// 切换主画面
const selectCamera = (id: number) => {
  selectedCameraId.value = id
}

const goToDetail = (id: number) => router.push(`/alert/${id}`)

// 纯视觉展示的工具栏按钮
const toolbarButtons = [
  { icon: '🔍+', label: '放大' }, { icon: '🔍-', label: '缩小' },
  { icon: '📷', label: '抓拍' }, { icon: '📹', label: '录像' },
  { icon: '➕', label: '云台控制' }, { icon: '💾', label: '保存预置位' },
  { icon: '⚙️', label: '设置' }, { icon: '📱', label: '切换布局' },
]
</script>

<template>
  <div class="h-screen w-full flex flex-col bg-[#111827] text-gray-200 p-4 gap-4 overflow-hidden font-sans">
    <header class="flex justify-between items-center pb-2 border-b border-[#374151] flex-shrink-0">
      <div class="flex items-center gap-3">
        <span class="text-3xl text-[#60A5FA]">■</span>
        <h1 class="text-2xl font-extrabold tracking-wider text-[#60A5FA]">尖兵视频安全识别系统</h1>
      </div>
      <button @click="router.push('/admin')" class="px-5 py-1.5 bg-[#3B82F6] hover:bg-[#60A5FA] text-white rounded-md border border-[#374151] transition-colors shadow-lg font-semibold text-xs">
        进入后台配置
      </button>
    </header>

    <main class="flex-1 flex gap-4 min-h-0">
      <div class="w-[72%] flex flex-col gap-4">
        
        <div class="h-[65%] bg-[#1F2937] rounded-xl border border-[#374151] p-4 flex flex-col shadow-xl">
          <h2 class="text-lg font-semibold mb-3 text-[#60A5FA] border-b border-[#374151] pb-2 flex justify-between">
              <span>实时视频矩阵</span>
              <span class="text-xs text-gray-400 font-normal">在线流: {{cameras.length}} 路</span>
          </h2>
          
          <div class="flex-1 flex gap-3 min-h-0 relative">
            
            <div class="flex-1 bg-black rounded-lg border border-[#374151] relative overflow-hidden">
              <img 
                v-if="selectedCameraStreamUrl"
                :src="selectedCameraStreamUrl" 
                class="w-full h-full object-contain" 
                alt="Main Live Stream"
              />
              <div v-else class="absolute inset-0 flex items-center justify-center text-gray-700 font-bold">
                请选择视频源
              </div>
              
              <div class="absolute top-3 left-3 bg-black/70 px-3 py-1.5 rounded text-sm text-white border border-gray-600/50">
                 <span class="w-2 h-2 inline-block rounded-full bg-green-500 mr-2 animate-pulse"></span>
                 {{ cameras.find(c => c.id === selectedCameraId)?.name || '未选择' }}
              </div>
            </div>

            <div class="w-[22%] bg-[#111827] rounded-lg border border-[#374151] p-2 flex flex-col">
              <div class="flex-1 overflow-y-auto pr-1 space-y-2 custom-scrollbar">
                 <button 
                   v-for="cam in cameras" :key="cam.id" 
                   @click="selectCamera(cam.id)"
                   class="w-full relative bg-black rounded border-2 overflow-hidden aspect-video group transition-all"
                   :class="cam.id === selectedCameraId ? 'border-[#60A5FA]' : 'border-[#374151] hover:border-gray-400'"
                 >
                   <img 
                     :src="`http://127.0.0.1:8000/api/video_feed/${cam.id}`" 
                     class="w-full h-full object-cover group-hover:opacity-80" 
                   />
                   <div class="absolute bottom-0 left-0 w-full bg-black/60 text-white text-[10px] text-left px-2 py-1 truncate">
                      {{ cam.name }}
                   </div>
                 </button>
              </div>
            </div>

          </div>
        </div>
        <div class="h-[35%] flex gap-4">
          <div class="w-1/2 bg-[#1F2937] rounded-xl border border-[#374151] p-4 flex flex-col font-mono text-sm shadow-xl relative">
            <h2 class="text-gray-400 mb-3 font-sans font-semibold">系统控制台</h2>
            <div class="flex-1 bg-black/40 rounded-lg p-3 overflow-y-auto space-y-1 text-[#60A5FA]/90 flex flex-col-reverse">
              <div><div v-for="(log, i) in logs" :key="i">> {{ log }}</div></div>
            </div>
          </div>
          <div class="w-1/2 bg-[#1F2937] rounded-xl border border-[#374151] p-4 flex flex-col shadow-xl relative">
            <h2 class="text-[#EF4444] mb-3 font-sans font-semibold flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-[#EF4444] animate-pulse"></span>当前最新 AI 识别画面
            </h2>
            <div class="flex-1 bg-black/40 rounded-lg overflow-hidden relative border border-[#374151]/50" v-if="latestAlert">
               <BboxImage :image-url="latestAlert.img" :label="latestAlert.type" :boxes="latestAlert.boxes || []" class="w-full h-full object-contain"/>
               <div class="absolute bottom-0 w-full bg-black/80 px-3 py-2 text-xs text-gray-300">[{{latestAlert.time}}] {{ latestAlert.camera }}</div>
            </div>
            <div v-else class="flex-1 flex items-center justify-center text-gray-500 bg-black/40 rounded-lg">暂无识别结果</div>
          </div>
        </div>
      </div>

      <div class="w-[28%] bg-[#1F2937] rounded-xl border border-[#374151] p-4 flex flex-col shadow-2xl">
        <h2 class="text-lg font-semibold mb-4 text-[#EF4444] border-b border-[#374151] pb-2 flex justify-between">
          <span>安全风险列表</span>
        </h2>
        <div class="flex-1 overflow-y-auto space-y-3 pr-1">
          <div v-for="alert in alerts" :key="alert.id" @click="goToDetail(alert.id)" class="flex gap-3 bg-[#111827] rounded-lg p-3 border border-[#374151] hover:border-[#EF4444] cursor-pointer transition-colors group">
            <img :src="alert.img" class="w-20 h-20 object-cover rounded border border-[#374151] group-hover:border-[#EF4444]" />
            <div class="flex-1 flex flex-col justify-between">
              <div class="flex justify-between items-start"><span class="text-[#EF4444] font-bold text-sm">{{ alert.type }}</span><span class="text-xs text-gray-500 font-mono">{{ alert.time }}</span></div>
              <p class="text-xs text-gray-400">{{ alert.camera }}</p>
              <p class="text-xs text-gray-300 line-clamp-2 mt-1">{{ alert.desc }}</p>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
/* 隐藏滚动条但保留滚动功能 */
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #374151;
  border-radius: 4px;
}
</style>