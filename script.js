var style = document.createElement("style");
style.innerHTML = `
#particles-js { 
    width: 100%; 
    height: 100%; 
    position: fixed; 
} 
.markdown-body {
    position: absolute;
}
body { 
    background-color: black; 
    color: white; 
}`;
document.head.appendChild(style);

var particlesDiv = document.createElement("div");
particlesDiv.setAttribute("id", "particles-js");
document.body.appendChild(particlesDiv);

var particlesScript = document.createElement("script");
particlesScript.setAttribute("src", "https://cdn.jsdelivr.net/npm/particles.js@2.0.0/particles.min.js");
document.body.appendChild(particlesScript);

var configScript = document.createElement("script");
configScript.setAttribute("src", "https://gdjkhp.github.io/meeseeks-leaderboard-api/particlesjs-config.js");
document.body.appendChild(configScript);