declare global {
  interface Window {
    AMap?: any
    _AMapSecurityConfig?: {
      securityJsCode?: string
    }
    __amapLoaderPromise__?: Promise<any>
  }
}

const parseEnvFlag = (raw: unknown, fallback = false) => {
  const text = String(raw ?? '').trim().toLowerCase()
  if (!text) return fallback
  return !['0', 'false', 'no', 'off'].includes(text)
}

const AMAP_JS_KEY = String(import.meta.env.VITE_AMAP_JS_KEY || '').trim()
const AMAP_SECURITY_JS_CODE = String(import.meta.env.VITE_AMAP_SECURITY_JS_CODE || '').trim()
const AMAP_ENABLED = parseEnvFlag(import.meta.env.VITE_ENABLE_LOGISTICS_MAP, false)

export const isAmapEnabled = () => AMAP_ENABLED && !!AMAP_JS_KEY

export const loadAmap = async () => {
  if (!isAmapEnabled()) {
    throw new Error('map_feature_disabled')
  }
  if (window.AMap) {
    return window.AMap
  }
  if (window.__amapLoaderPromise__) {
    return window.__amapLoaderPromise__
  }

  if (AMAP_SECURITY_JS_CODE) {
    window._AMapSecurityConfig = {
      securityJsCode: AMAP_SECURITY_JS_CODE
    }
  }

  window.__amapLoaderPromise__ = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.async = true
    script.defer = true
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(AMAP_JS_KEY)}`
    script.onload = () => {
      if (window.AMap) {
        resolve(window.AMap)
        return
      }
      reject(new Error('map_sdk_missing'))
    }
    script.onerror = () => {
      reject(new Error('map_sdk_load_failed'))
    }
    document.head.appendChild(script)
  })

  try {
    return await window.__amapLoaderPromise__
  } catch (err) {
    window.__amapLoaderPromise__ = undefined
    throw err
  }
}

