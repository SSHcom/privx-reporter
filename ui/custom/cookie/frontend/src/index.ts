import { RenderData, Streamlit } from "streamlit-component-lib"

type CookieValue = string | number | boolean
type CookieOptions = {
  path?: string
  expires?: string
  maxAge?: number
  domain?: string
  secure?: boolean
  sameSite?: "lax" | "strict" | "none"
}

let lastOutput = ""

function parseCookies(): Record<string, string> {
  const parsed: Record<string, string> = {}
  const rawCookies = document.cookie ? document.cookie.split("; ") : []
  for (const item of rawCookies) {
    const separatorIndex = item.indexOf("=")
    if (separatorIndex < 0) {
      continue
    }
    const name = decodeURIComponent(item.slice(0, separatorIndex))
    const value = decodeURIComponent(item.slice(separatorIndex + 1))
    parsed[name] = value
  }
  return parsed
}

function setCookie(cookie: string, value: CookieValue, options: CookieOptions): boolean {
  const parts = [
    `${encodeURIComponent(cookie)}=${encodeURIComponent(String(value))}`,
    `Path=${options.path ?? "/"}`,
  ]

  if (options.expires) {
    const expires = new Date(options.expires)
    if (!Number.isNaN(expires.getTime())) {
      parts.push(`Expires=${expires.toUTCString()}`)
    }
  }
  if (typeof options.maxAge === "number") {
    parts.push(`Max-Age=${Math.floor(options.maxAge)}`)
  }
  if (options.domain) {
    parts.push(`Domain=${options.domain}`)
  }
  if (options.secure) {
    parts.push("Secure")
  }
  if (options.sameSite) {
    parts.push(`SameSite=${options.sameSite}`)
  }

  document.cookie = parts.join("; ")
  return true
}

function deleteCookie(cookie: string, options: CookieOptions): boolean {
  const parts = [
    `${encodeURIComponent(cookie)}=`,
    `Path=${options.path ?? "/"}`,
    "Max-Age=0",
  ]
  if (options.domain) {
    parts.push(`Domain=${options.domain}`)
  }
  document.cookie = parts.join("; ")
  return true
}

function onRender(event: Event): void {
  const data = (event as CustomEvent<RenderData>).detail
  const method = data.args["method"] as string | undefined
  const cookie = data.args["cookie"] as string | undefined
  const value = data.args["value"] as CookieValue | undefined
  const options = (data.args["options"] ?? {}) as CookieOptions

  let output: unknown = null
  switch (method) {
    case "set":
      output = cookie ? setCookie(cookie, value ?? "", options) : false
      break
    case "get":
      output = cookie ? parseCookies()[cookie] ?? null : null
      break
    case "getAll":
      output = parseCookies()
      break
    case "delete":
      output = cookie ? deleteCookie(cookie, options) : false
      break
    default:
      output = null
  }

  const serializedOutput = JSON.stringify(output)
  if (serializedOutput !== lastOutput) {
    lastOutput = serializedOutput
    Streamlit.setComponentValue(output)
  }
  Streamlit.setFrameHeight(0)
}

Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender)
Streamlit.setComponentReady()
Streamlit.setFrameHeight(0)
