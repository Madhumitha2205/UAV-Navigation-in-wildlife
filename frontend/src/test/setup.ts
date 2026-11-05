import '@testing-library/jest-dom'

class MockWebSocket {
  url: string
  readyState: number = 0
  onopen: ((ev: any) => any) | null = null
  onclose: ((ev: any) => any) | null = null
  onmessage: ((ev: any) => any) | null = null
  onerror: ((ev: any) => any) | null = null

  constructor(url: string) {
    this.url = url
    setTimeout(() => {
      this.readyState = 1
      if (this.onopen) {
        this.onopen({ type: 'open' })
      }
    }, 0)
  }

  send() {}
  close() {
    this.readyState = 3
    if (this.onclose) {
      this.onclose({ type: 'close' })
    }
  }
  addEventListener() {}
  removeEventListener() {}
  dispatchEvent() {
    return true
  }
}

globalThis.WebSocket = MockWebSocket as unknown as typeof WebSocket
