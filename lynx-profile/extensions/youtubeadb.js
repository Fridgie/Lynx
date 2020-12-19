const clear = (() => {
    const defined = v => v !== null && v !== undefined;
    const timeout = setInterval(() => {
        const ad = [...document.querySelectorAll('.ad-showing')][0];
        if (defined(ad)) {
            const video = document.querySelector('video');
            if (defined(video)) {
                video.currentTime = video.duration;
            }
        } 
    }, 500);
    return function() {
        clearTimeout(timeout);
    }
})();

document.addEventListener("keypress", function(event) {
    if (event.keyCode == 13) {
        clear(); 
    }
});

var cssId = 'myCss';
if (!document.getElementById(cssId))
{
    var head  = document.getElementsByTagName('head')[0];
    var link  = document.createElement('link');
    link.id   = cssId;
    link.rel  = 'stylesheet';
    link.type = 'text/css';
    link.href = 'https://www.gozer.org/mozilla/ad_blocking/css/ad_blocking.css';
    link.media = 'all';
    head.appendChild(link);
}
