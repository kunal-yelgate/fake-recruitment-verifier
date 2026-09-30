const MAX_TEXT_LENGTH = 9999;

const SELECTORS = [
  // LinkedIn job pages
  ".jobs-description__content",
  ".jobs-box__html-content",
  // Naukri job pages
  ".job-desc",
  ".jd-container",
  // Indeed job pages
  "#jobDescriptionText",
  ".jobsearch-JobComponent-description"
];

function extractPageText() {
  const sections = SELECTORS
    .map((selector) => document.querySelector(selector)?.innerText || "")
    .filter(Boolean);
  const text = (sections.length ? sections.join("\n\n") : document.body?.innerText || "")
    .replace(/\s+/g, " ")
    .trim();
  return text.slice(0, MAX_TEXT_LENGTH);
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type !== "extractPageText") return;
  sendResponse({ text: extractPageText() });
});
