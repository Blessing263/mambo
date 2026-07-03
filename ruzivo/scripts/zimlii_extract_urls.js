// ZimLII Judgment URL Extractor
// Paste into Chrome DevTools Console on https://zimlii.org/judgments/
// Auto-scrolls infinite-scroll page, extracts all judgment links, downloads JSON

(async () => {
    const seen = new Set();
    let prevCount = 0;
    let noNew = 0;

    // Scroll to load more (infinite scroll)
    while (true) {
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise(r => setTimeout(r, 2000));

        const links = document.querySelectorAll('a[href*="/akn/zw/judgment/"]');
        links.forEach(a => seen.add(a.href));

        if (seen.size === prevCount) {
            noNew++;
            if (noNew >= 4) break; // no new links after 4 scrolls = done
        } else {
            noNew = 0;
            prevCount = seen.size;
            console.log(`Collected: ${seen.size} judgment URLs...`);
        }
    }

    const urls = [...seen].sort();
    console.log(`\nDone! ${urls.length} judgment URLs collected.`);

    // Auto-download as JSON
    const blob = new Blob([JSON.stringify(urls, null, 2)], {type: 'application/json'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'zimlii_judgment_urls.json';
    a.click();
    console.log('Downloaded: zimlii_judgment_urls.json');
    return urls;
})();
