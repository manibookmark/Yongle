const edition = document.querySelector("#edition");
const copy = document.querySelector("#copy");
const size = document.querySelector("#size");
const preview = document.querySelector("#preview");
const status = document.querySelector("#font-status");
const samples = document.querySelector("#samples");
const sizeValue = document.querySelector("#size-value");

const editions = {
  sc: {
    family: "Yongle Web SC",
    lang: "zh-CN",
    samples: ["永乐大典", "大明藏书", "中国古典", "山水之间", "本草经", "坚强意志", "墙边清泉", "神采飞扬", "永乐 Yongle 2026"],
  },
  latin: {
    family: "Yongle Web Latin",
    lang: "en",
    samples: ["Yongle", "The Art of Type", "Aa Bb Cc 0123456789", '"Light & Shadow"'],
  },
};
const supported = Object.fromEntries(Object.entries(coverage).map(([id, chars]) => [id, new Set(chars)]));
const loaded = new Map();
let custom = false;
let updateId = 0;

function updateSize() {
  preview.style.setProperty("--specimen-size", size.value + "px");
  sizeValue.value = size.value + " px";
}

async function updatePreview() {
  const id = ++updateId;
  const key = edition.value;
  const current = editions[key];
  preview.dataset.edition = key;
  preview.lang = current.lang;
  preview.textContent = copy.value;
  status.textContent = "正在加载字体…";
  if (!loaded.has(key)) {
    const request = document.fonts.load('36px "' + current.family + '"', current.samples[0])
      .then(faces => faces.some(face => face.status === "loaded"))
      .catch(() => false);
    loaded.set(key, request);
  }
  if (!(await loaded.get(key))) {
    loaded.delete(key);
    if (id === updateId) status.textContent = "字体加载失败，请刷新页面重试。";
    return;
  }
  if (id !== updateId) return;
  const missing = [...new Set([...copy.value].filter(char => !/\s/u.test(char) && !supported[key].has(char)))];
  status.textContent = missing.length
    ? "字体已加载。以下字符使用系统字体：" + missing.slice(0, 12).join(" ") + (missing.length > 12 ? " 等" : "")
    : "字体已加载";
}

function updateEdition() {
  const choices = editions[edition.value].samples;
  if (!custom) copy.value = choices[0];
  samples.replaceChildren(...choices.map(sample => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = sample;
    button.addEventListener("click", () => {
      custom = false;
      copy.value = sample;
      updatePreview();
    });
    return button;
  }));
  updatePreview();
}

edition.addEventListener("change", updateEdition);
copy.addEventListener("input", () => {
  custom = true;
  updatePreview();
});
size.addEventListener("input", updateSize);
document.querySelectorAll("[data-size]").forEach(button => {
  button.addEventListener("click", () => {
    size.value = button.dataset.size;
    updateSize();
  });
});
updateSize();
updateEdition();
