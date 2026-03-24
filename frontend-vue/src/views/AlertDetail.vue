<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import BboxImage from '../components/BboxImage.vue'

const router = useRouter()
const route = useRoute()

// 1. 将静态对象改为 ref 响应式对象
const alertData = ref<any>({
  id: route.params.id,
  time: '',
  camera: '',
  type: '正在加载...',
  desc: '',
  img: '', 
  boxes: [] 
})

onMounted(async () => {
  const backendBaseUrl = `http://${window.location.hostname}:8000`
  try {
    // 2. 从后端获取对应 ID 的真实数据
    // 这里采用拉取历史记录过滤的方式，如果后端有写单条查询接口 (如 /api/alerts/{id}) 更好
    const historyRes = await fetch(`${backendBaseUrl}/api/alerts/history?limit=50`) 
    const historyData = await historyRes.json()
    
    // 寻找匹配当前路由 ID 的告警记录
    const currentAlert = historyData.find((item: any) => String(item.id) === String(route.params.id))
    
    if (currentAlert) {
      alertData.value = {
        ...currentAlert,
        // 确保图片路径是完整的
        img: currentAlert.img.startsWith('http') ? currentAlert.img : `${backendBaseUrl}${currentAlert.img}`
      }
    } else {
      alertData.value.desc = '未找到该告警记录信息或已被清理'
    }
  } catch (error) {
    console.error('获取告警详情失败:', error)
    alertData.value.desc = '数据获取失败，请检查网络连接'
  }
})
</script>

<template>
  <div class="min-h-screen bg-[#111827] text-gray-200 p-8 flex flex-col items-center">
    <div class="w-full max-w-5xl">
      <button @click="router.push('/')" class="mb-6 text-[#60A5FA] hover:text-white flex items-center gap-2 transition-colors">
        <span>← 返回监控大屏</span>
      </button>

      <div v-if="alertData.img" class="bg-[#1F2937] border border-[#374151] rounded-xl shadow-2xl p-6 flex flex-col gap-6">
        <div class="flex justify-between items-center border-b border-[#374151] pb-4">
          <div>
            <h1 class="text-3xl font-bold text-[#EF4444] mb-2">{{ alertData.type }}</h1>
            <p class="text-gray-400">发生设备: {{ alertData.camera }} | 记录时间: {{ alertData.time }} | 事件ID: {{ alertData.id }}</p>
          </div>
          <span class="px-4 py-2 bg-[#EF4444]/20 text-[#EF4444] font-bold rounded border border-[#EF4444]/50">待处理</span>
        </div>

        <div class="w-full max-w-3xl mx-auto">
          <BboxImage :image-url="alertData.img" :label="alertData.type" :boxes="alertData.boxes || []" />
        </div>

        <div class="bg-[#111827] p-4 rounded-lg border border-[#374151]">
          <h3 class="text-[#60A5FA] font-semibold mb-2">大模型智能分析描述：</h3>
          <p class="text-gray-300 leading-relaxed">{{ alertData.desc }}</p>
        </div>
      </div>
      
      <div v-else class="text-center text-gray-400 py-32 bg-[#1F2937] rounded-xl border border-[#374151]">
         {{ alertData.desc || '正在加载现场抓拍画面...' }}
      </div>
      
    </div>
  </div>
</template>