const $ = (id) => document.getElementById(id)

async function postJSON(url, payload) {
  const res = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)})
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || res.statusText)
  }
  return res.json()
}

function appendMessage(who, text, opts = {}){
  const h = $('history')
  const el = document.createElement('div')
  el.className = 'msg ' + who
  const timestamp = opts.timestamp || new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})

  // message content
  const content = document.createElement('div')
  content.className = 'msg-text'
  const messageInner = document.createElement('div')
  messageInner.className = 'message-content'
  messageInner.textContent = text
  content.appendChild(messageInner)

  // actions (copy) for assistant
  if (who === 'assistant'){
    const actions = document.createElement('div')
    actions.className = 'msg-actions'
    const copyBtn = document.createElement('button')
    copyBtn.className = 'copy-btn'
    copyBtn.type = 'button'
    copyBtn.textContent = 'Copy'
    copyBtn.title = 'Copy answer'
    copyBtn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(text)
        const prev = copyBtn.textContent
        copyBtn.textContent = 'Copied'
        setTimeout(() => copyBtn.textContent = prev, 1400)
      } catch (e) {
        copyBtn.textContent = 'Failed'
        setTimeout(() => copyBtn.textContent = 'Copy', 1400)
      }
    })
    actions.appendChild(copyBtn)
    content.appendChild(actions)
  }

  const meta = document.createElement('div')
  meta.className = 'msg-meta'
  meta.innerHTML = `<span class="time">${escapeHtml(timestamp)}</span>`

  el.appendChild(content)
  el.appendChild(meta)
  h.appendChild(el)
  h.scrollTop = h.scrollHeight
}

function appendContexts(contexts){
  if (!contexts || contexts.length === 0) return
  const h = $('history')
  const container = document.createElement('div')
  container.className = 'contexts'
  const title = document.createElement('div')
  title.className = 'meta-title'
  title.textContent = 'Contexts:'
  container.appendChild(title)

  const limit = 400
  contexts.forEach(c => {
    const ctx = document.createElement('div')
    ctx.className = 'context'

    const full = c.text || ''
    const textDiv = document.createElement('div')
    textDiv.className = 'context-text'

    if (full.length > limit){
      const shortSpan = document.createElement('span')
      shortSpan.className = 'short'
      shortSpan.textContent = full.slice(0, limit) + '… '

      const fullSpan = document.createElement('span')
      fullSpan.className = 'full hidden'
      fullSpan.textContent = full + ' '

      const toggle = document.createElement('button')
      toggle.className = 'toggle-ctx'
      toggle.type = 'button'
      toggle.textContent = 'Show more'
      toggle.addEventListener('click', () => {
        const isExpanded = fullSpan.classList.toggle('hidden')
        shortSpan.classList.toggle('hidden')
        toggle.textContent = isExpanded ? 'Show less' : 'Show more'
      })

      textDiv.appendChild(shortSpan)
      textDiv.appendChild(fullSpan)
      textDiv.appendChild(toggle)
    } else {
      textDiv.textContent = full
    }

    ctx.appendChild(textDiv)

    if (c.metadata){
      const meta = document.createElement('div')
      meta.className = 'context-meta'
      for (const [k,v] of Object.entries(c.metadata)){
        const d = document.createElement('div')
        d.className = 'meta'
        d.innerHTML = `<strong>${escapeHtml(k)}:</strong> ${escapeHtml(String(v))}`
        meta.appendChild(d)
      }
      ctx.appendChild(meta)
    }

    const copyBtn = document.createElement('button')
    copyBtn.className = 'copy-btn'
    copyBtn.type = 'button'
    copyBtn.textContent = 'Copy'
    copyBtn.title = 'Copy context text'
    copyBtn.addEventListener('click', async () => {
      try{
        await navigator.clipboard.writeText(full)
        const prev = copyBtn.textContent
        copyBtn.textContent = 'Copied'
        setTimeout(() => copyBtn.textContent = prev, 1400)
      } catch(e){
        copyBtn.textContent = 'Failed'
        setTimeout(() => copyBtn.textContent = 'Copy', 1400)
      }
    })
    ctx.appendChild(copyBtn)

    container.appendChild(ctx)
  })

  h.appendChild(container)
  h.scrollTop = h.scrollHeight
}

function appendLoading(){
  const h = $('history')
  const el = document.createElement('div')
  el.className = 'msg system loading'
  el.innerHTML = `<div class="msg-text"><span class="spinner" aria-hidden="true"></span> Loading…</div>`
  h.appendChild(el)
  h.scrollTop = h.scrollHeight
  return el
}

function removeLoading(el){
  if (el && el.remove) el.remove()
}

$('send-btn').addEventListener('click', async () => {
  const msg = $('message').value.trim()
  if (!msg) return
  const useRag = $('use-rag').checked

  $('message').value = ''
  appendMessage('user', msg, {timestamp: new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})})
  const loader = appendLoading()

  try {
    const payload = {message: msg, use_rag: useRag}
    const res = await postJSON('/chat', payload)
    removeLoading(loader)
    appendMessage('assistant', res.answer)
    if (res.contexts && res.contexts.length) appendContexts(res.contexts)
  } catch (err) {
    removeLoading(loader)
    appendMessage('system', `Error: ${err.message}`)
  }
})

$('clear-btn').addEventListener('click', () => { $('message').value = ''; $('history').innerHTML = '' })

// Enter to send (Shift+Enter for newline)
$('message').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    $('send-btn').click()
  }
})

// Fullscreen toggle
$('fullscreen-btn').addEventListener('click', () => {
  document.getElementById('app').classList.toggle('fullscreen')
})

// Theme toggle (persist to localStorage)
const themeToggle = $('theme-toggle')
function setTheme(dark){
  if (dark) {
    document.body.classList.add('dark')
    localStorage.setItem('theme','dark')
  } else {
    document.body.classList.remove('dark')
    localStorage.setItem('theme','light')
  }
}
const savedTheme = localStorage.getItem('theme') || (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
setTheme(savedTheme === 'dark')
if (themeToggle) themeToggle.addEventListener('click', () => setTheme(!document.body.classList.contains('dark')))

function escapeHtml(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') }
