const form = document.getElementById('upload-form');
const statusEl = document.getElementById('status');
const metaCard = document.getElementById('meta-card');
const visualsCard = document.getElementById('visuals-card');
const videoCard = document.getElementById('video-card');
const genVisualsBtn = document.getElementById('gen-visuals');
const genVideoBtn = document.getElementById('gen-video');
const spinner = document.getElementById('spinner');
const toast = document.getElementById('toast');
const modal = document.getElementById('modal');
const modalImg = document.getElementById('modal-img');
const modalClose = document.getElementById('modal-close');
const modalDownload = document.getElementById('modal-download');
let lastImagePath = null;
let lastGeneratedVisuals = [];

function showSpinner(){ spinner.style.display = 'flex' }
function hideSpinner(){ spinner.style.display = 'none' }
function showToast(msg, timeout=3500){ toast.textContent = msg; toast.style.display='block'; setTimeout(()=>{ toast.style.display='none'; }, timeout) }
function openModal(src){ modalImg.src = src; modal.style.display = 'flex'; modalDownload.href = src }
modalClose?.addEventListener('click', ()=> modal.style.display='none')
modal?.addEventListener('click', (e)=>{ if(e.target === modal) modal.style.display='none' })

function setStatus(msg, isError=false){ statusEl.textContent = msg; statusEl.style.color = isError ? '#dc2626' : '#065f46'; }

form.addEventListener('submit', async (e) =>{
  e.preventDefault();
  setStatus('Uploading image & generating metadata...');
  showSpinner();
  const data = new FormData(form);
  try{
    const res = await fetch('/generate-metadata', { method: 'POST', body: data });
    const payload = await res.json();
    if(!res.ok){ throw new Error(payload.detail || payload.error || 'Server error'); }
    lastImagePath = payload.image_path;
    document.getElementById('metadata').innerHTML = `<pre>${JSON.stringify(payload, null, 2)}</pre>`;
    metaCard.style.display = 'block';
    genVisualsBtn.disabled = false;
    showToast('Metadata generated');
    setStatus('Metadata generated ✅');
  }catch(err){ setStatus('Failed to generate metadata', true); showToast('Metadata failed'); console.error(err); }
  hideSpinner();
});

function renderGallery(list){ const gallery = document.getElementById('visuals'); gallery.innerHTML = ''; list.forEach((u,i)=>{ const fig = document.createElement('figure'); const img = document.createElement('img'); img.src = u.startsWith('/') ? u : ('/' + u.replaceAll('\\\\','/')); img.alt = `visual-${i}`; img.addEventListener('click', ()=>openModal(img.src)); const cap = document.createElement('figcaption'); cap.innerHTML = `<span>Visual ${i+1}</span> <a href="${img.src}" download>Download</a>`; fig.appendChild(img); fig.appendChild(cap); gallery.appendChild(fig); }) }

genVisualsBtn.addEventListener('click', async ()=>{
  if(!lastImagePath){ setStatus('No image available to generate visuals', true); showToast('No uploaded image'); return; }
  setStatus('Generating supplementary visuals...');
  genVisualsBtn.disabled = true; showSpinner();
  try{
    const body = { image_path: lastImagePath, title: document.getElementById('category').value || 'Product' };
    const res = await fetch('/api/generate-visuals', { method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify(body) });
    const j = await res.json();
    if(!res.ok){ throw new Error(j.error || 'Failed'); }
    lastGeneratedVisuals = j.generated;
    renderGallery(j.generated);
    visualsCard.style.display = 'block';
    genVideoBtn.disabled = false;
    showToast('Visuals ready');
    setStatus('Visuals ready ✅');
  }catch(e){ setStatus('Failed to generate visuals', true); showToast('Visuals failed'); console.error(e); }
  genVisualsBtn.disabled = false; hideSpinner();
});

genVideoBtn.addEventListener('click', async ()=>{
  if(!lastGeneratedVisuals.length){ setStatus('No visuals available', true); showToast('No visuals'); return; }
  setStatus('Building slideshow video (ffmpeg required)...');
  genVideoBtn.disabled = true; showSpinner();
  try{
    const res = await fetch('/api/generate-video', { method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify({ frames: lastGeneratedVisuals, fps: 2, tts: `Introducing this product: ${document.getElementById('category').value || 'A fine product'}` }) });
    const j = await res.json();
    if(!res.ok){ throw new Error(j.error || 'Failed'); }
    const videoUrl = j.video_url;
    const video = document.getElementById('preview-video');
    video.src = videoUrl;
    document.getElementById('video-link').innerHTML = `<a href="${videoUrl}" target="_blank">Download video</a>`;
    videoCard.style.display = 'block';
    showToast('Video ready');
    setStatus('Video ready ✅');
  }catch(e){ setStatus('Failed to build video', true); showToast('Video failed'); console.error(e); }
  genVideoBtn.disabled = false; hideSpinner();
});

// small enhancement: click metadata to copy
const metadataEl = document.getElementById('metadata');
metadataEl?.addEventListener('click', ()=>{ try{ navigator.clipboard.writeText(metadataEl.textContent || ''); showToast('Metadata copied to clipboard'); }catch(e){} })

