<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import BboxImage from '../components/BboxImage.vue'

const router = useRouter()
const route = useRoute()

// 实际开发中，这里会根据 route.params.id 向后端发起请求获取详情
// 这里先用写死的数据展示结构
const alertData = {
  id: route.params.id,
  time: '17:31:14',
  camera: 'Cam-02 生产车间A区',
  type: '未戴安全帽',
  desc: '系统检测到画面左侧有一名工人未佩戴标准安全帽，已记录违规并上报数据库。',
  img: 'https://images.unsplash.com/photo-1504328345606-18bbc8c9d7d1?q=80&w=800&auto=format&fit=crop', 
  boxes: [{ x: 45, y: 20, w: 15, h: 20 }] 
}
</script>

<template>
  <div class="min-h-screen bg-[#111827] text-gray-200 p-8 flex flex-col items-center">
    <div class="w-full max-w-5xl">
      <button @click="router.push('/')" class="mb-6 text-[#60A5FA] hover:text-white flex items-center gap-2 transition-colors">
        <span>← 返回监控大屏</span>
      </button>

      <div class="bg-[#1F2937] border border-[#374151] rounded-xl shadow-2xl p-6 flex flex-col gap-6">
        <div class="flex justify-between items-center border-b border-[#374151] pb-4">
          <div>
            <h1 class="text-3xl font-bold text-[#EF4444] mb-2">{{ alertData.type }}</h1>
            <p class="text-gray-400">发生设备: {{ alertData.camera }} | 记录时间: {{ alertData.time }} | 事件ID: {{ alertData.id }}</p>
          </div>
          <span class="px-4 py-2 bg-[#EF4444]/20 text-[#EF4444] font-bold rounded border border-[#EF4444]/50">待处理</span>
        </div>

        <div class="w-full max-w-3xl mx-auto">
          <BboxImage :image-url="alertData.img" :label="alertData.type" :boxes="alertData.boxes" />
        </div>

        <div class="bg-[#111827] p-4 rounded-lg border border-[#374151]">
          <h3 class="text-[#60A5FA] font-semibold mb-2">大模型智能分析描述：</h3>
          <p class="text-gray-300 leading-relaxed">{{ alertData.desc }}</p>
        </div>
      </div>
    </div>
  </div>
</template>