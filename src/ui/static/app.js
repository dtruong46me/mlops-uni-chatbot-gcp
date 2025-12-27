const $ = (id) => document.getElementById(id)

// Tabs
$('tab-ask').addEventListener('click', () => { $('tab-ask').classList.add('active'); $('tab-llm').classList.remove('active'); $('panel-ask').classList.remove('hidden'); $('panel-llm').classList.add('hidden') })
$('tab-llm').addEventListener('click', () => { $('tab-llm').classList.add('active'); $('tab-ask').classList.remove('active'); $('panel-llm').classList.remove('hidden'); $('panel-ask').classList.add('hidden') })

async function postJSON(url, payload) {
  const res = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)})
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || res.statusText)
  }
  return res.json()
}

$('ask-btn').addEventListener('click', async () => {
  const q = $('question').value.trim()
  if (!q) return alert('Please enter a question')
  $('answer-area').innerHTML = 'Loading...'
  try {
    const data = await postJSON('/ask', {question: q})
    const html = `
      <div class="answer"><strong>Answer:</strong><div>${escapeHtml(data.answer)}</div></div>
      <div class="answer"><strong>Contexts:</strong>${data.contexts.map(c => `<div>${escapeHtml(c.text)}</div>`).join('')}</div>`
    $('answer-area').innerHTML = html
  } catch (err) {
    $('answer-area').innerHTML = `<div class="answer">Error: ${escapeHtml(err.message)}</div>`
  }
})

$('llm-btn').addEventListener('click', async () => {
  const p = $('prompt').value.trim()
  if (!p) return alert('Please enter a prompt')
  $('llm-area').innerHTML = 'Loading...'
  try {
    const data = await postJSON('/llm/answer', {prompt: p})
    $('llm-area').innerHTML = `<div class="answer"><strong>Answer:</strong><div>${escapeHtml(data.answer)}</div></div>`
  } catch (err) {
    $('llm-area').innerHTML = `<div class="answer">Error: ${escapeHtml(err.message)}</div>`
  }
})

function escapeHtml(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') }
