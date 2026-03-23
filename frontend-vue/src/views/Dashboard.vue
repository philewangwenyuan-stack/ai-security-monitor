<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const cameras = ref([
  { id: 1, name: 'Cam-01 南门主干道', status: 'Online' },
  { id: 2, name: 'Cam-02 生产车间A区', status: 'Online' },
])

const logs = ref([
  '[17:30:01] 终端控制台启动...',
  '[17:31:14] Cam-02 分析完成，发现异常事件.'
])

// 告警列表数据
const alerts = ref([
  {
    id: 101,
    time: '17:31:14',
    camera: 'Cam-02 生产车间A区',
    type: '未戴安全帽',
    desc: '画面左侧有一名工人未佩戴标准安全帽。',
    img: 'https://images.unsplash.com/photo-1504328345606-18bbc8c9d7d1?q=80&w=800&auto=format&fit=crop', 
  }
])

const goToDetail = (id: number) => {
  router.push(`/alert/${id}`)
}
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
      <div class="w-[65%] flex flex-col gap-4">
        <div class="h-[60%] bg-[#1F2937] rounded-xl border border-[#374151] p-4 flex flex-col shadow-xl">
          <h2 class="text-lg font-semibold mb-4 text-[#60A5FA] border-b border-[#374151] pb-2">实时监控网格</h2>
          <div class="flex-1 grid grid-cols-2 gap-4 min-h-0">
            <div v-for="cam in cameras" :key="cam.id" class="relative bg-black rounded-lg border border-[#374151] flex items-center justify-center">
              <span class="text-gray-700 font-bold">RTSP STREAM LOAD...</span>
              <div class="absolute top-2 left-2 bg-black/70 px-2 py-1 rounded text-xs">
                <span class="w-2 h-2 inline-block rounded-full bg-green-500 mr-2"></span>{{ cam.name }}
              </div>
            </div>
          </div>
        </div>

        <div class="h-[40%] bg-[#1F2937] rounded-xl border border-[#374151] p-4 flex flex-col font-mono text-sm">
           <h2 class="text-gray-400 mb-3 font-sans font-semibold">系统交互控制台</h2>
           <div class="flex-1 bg-black/40 rounded-lg p-3 overflow-y-auto space-y-1 text-[#60A5FA]/90">
             <div v-for="(log, i) in logs" :key="i">> {{ log }}</div>
           </div>
        </div>
      </div>

      <div class="w-[35%] bg-[#1F2937] rounded-xl border border-[#374151] p-4 flex flex-col shadow-2xl">
        <h2 class="text-lg font-semibold mb-4 text-[#EF4444] border-b border-[#374151] pb-2 flex justify-between">
          <span>安全风险列表</span>
        </h2>
        
        <div class="flex-1 overflow-y-auto space-y-3 pr-1">
          <div v-for="alert in alerts" :key="alert.id" @click="goToDetail(alert.id)" 
               class="flex gap-3 bg-[#111827] rounded-lg p-3 border border-[#374151] hover:border-[#EF4444] cursor-pointer transition-colors group">
            <img :src="alert.img" class="w-20 h-20 object-cover rounded border border-[#374151] group-hover:border-[#EF4444]" />
            <div class="flex-1 flex flex-col justify-between">
              <div class="flex justify-between items-start">
                <span class="text-[#EF4444] font-bold text-sm">{{ alert.type }}</span>
                <span class="text-xs text-gray-500 font-mono">{{ alert.time }}</span>
              </div>
              <p class="text-xs text-gray-400">{{ alert.camera }}</p>
              <p class="text-xs text-gray-300 line-clamp-2 mt-1">{{ alert.desc }}</p>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>