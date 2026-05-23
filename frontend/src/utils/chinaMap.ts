/* 中国地图数据加载工具 */

import * as echarts from 'echarts'

const CHINA_MAP_URL = '/china.json'

let promise: Promise<void> | null = null

export function ensureChinaMap(): Promise<void> {
  if (promise) {
    return promise
  }

  promise = fetch(CHINA_MAP_URL)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      return response.json()
    })
    .then((geo) => {
      echarts.registerMap('china', geo)
    })
    .catch((e) => {
      promise = null
      console.error('[chinaMap] load failed', e)
      throw e
    })

  return promise
}

export const PROVINCE_FULL_NAME: Record<string, string> = {
  北京: '北京市',
  上海: '上海市',
  天津: '天津市',
  重庆: '重庆市',
  河北: '河北省',
  山西: '山西省',
  辽宁: '辽宁省',
  吉林: '吉林省',
  黑龙江: '黑龙江省',
  江苏: '江苏省',
  浙江: '浙江省',
  安徽: '安徽省',
  福建: '福建省',
  江西: '江西省',
  山东: '山东省',
  河南: '河南省',
  湖北: '湖北省',
  湖南: '湖南省',
  广东: '广东省',
  海南: '海南省',
  四川: '四川省',
  贵州: '贵州省',
  云南: '云南省',
  陕西: '陕西省',
  甘肃: '甘肃省',
  青海: '青海省',
  台湾: '台湾省',
  内蒙古: '内蒙古自治区',
  广西: '广西壮族自治区',
  西藏: '西藏自治区',
  宁夏: '宁夏回族自治区',
  新疆: '新疆维吾尔自治区',
  香港: '香港特别行政区',
  澳门: '澳门特别行政区',
}

export function toFullProvinceName(name: string): string {
  return PROVINCE_FULL_NAME[name] ?? name
}
