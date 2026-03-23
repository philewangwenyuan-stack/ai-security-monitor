<script setup lang="ts">
// 接收外部传来的图片地址和红框百分比坐标数组 x, y 是左上角坐标，w, h 是宽高
defineProps<{
  imageUrl: string;
  label: string;
  boxes: Array<{ x: number; y: number; w: number; h: number }>;
}>();
</script>

<template>
  <div class="relative w-full inline-block overflow-hidden rounded-lg bg-[#1F2937] border border-[#374151] shadow-inner">
    <img :src="imageUrl" class="w-full h-auto block" alt="Alert Frame" />
    
    <div
      v-for="(box, index) in boxes"
      :key="index"
      class="absolute border-2 border-[#EF4444] bg-[#EF4444]/20 box-border rounded-sm transition-all duration-300"
      :style="{
        left: box.x + '%',
        top: box.y + '%',
        width: box.w + '%',
        height: box.h + '%'
      }"
    >
      <span class="absolute -top-6 left-[-2px] bg-[#EF4444] text-white text-xs px-2 py-0.5 rounded-t font-bold shadow-md whitespace-nowrap">
        {{ label }}
      </span>
    </div>
  </div>
</template>