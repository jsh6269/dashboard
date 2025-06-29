function addItem() {
  const title = document.getElementById("title").value;
  const description = document.getElementById("desc").value;
  const formData = new FormData();
  formData.append("title", title);
  formData.append("description", description);
  const fileInput = document.getElementById("image");
  if (fileInput.files.length > 0) {
    formData.append("image", fileInput.files[0]);
  }

  fetch("http://localhost:8000/items", {
    method: "POST",
    body: formData,
  })
    .then((resp) => resp.json())
    .then((data) => {
      renderResults([data]);
    })
    .catch((err) => {
      document.getElementById(
        "result"
      ).innerHTML = `<p style='color:red;'>Error: ${err}</p>`;
    });
}

function searchItems() {
  const q = document.getElementById("query").value;
  fetch(`http://localhost:8000/search?q=${encodeURIComponent(q)}`)
    .then((resp) => resp.json())
    .then((data) => {
      if (Array.isArray(data.results)) {
        renderResults(data.results);
      } else {
        renderResults([]);
      }
    })
    .catch((err) => {
      document.getElementById(
        "result"
      ).innerHTML = `<p style='color:red;'>Error: ${err}</p>`;
    });
}

function formatDateTime(isoStr) {
  const d = new Date(isoStr);
  if (isNaN(d)) return isoStr;
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(
    d.getHours()
  )}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function renderResults(items) {
  const container = document.getElementById("result");
  if (!items || items.length === 0) {
    container.innerHTML = "<p>결과가 없습니다.</p>";
    return;
  }
  container.innerHTML = items
    .map((item) => {
      const imgTag = item.image_path
        ? `<img src="http://localhost:8000/${item.image_path}" style="max-width:100px;" />`
        : "";
      return `
        <div class="card">
          <h4>${item.title}</h4>
          <p>${item.description || ""}</p>
          ${imgTag}<br/>
          <small style="color:#666;">${
            item.created_at ? formatDateTime(item.created_at) : ""
          }</small>
        </div>
      `;
    })
    .join("");
}
