document.addEventListener('DOMContentLoaded', function() {
    const text = "L'université attendra votre candidature";
    const typewriterText = document.getElementById('typewriter-text');
    let i = 0;
    
    function typeWriter() {
        if (i < text.length) {
            typewriterText.innerHTML += text.charAt(i);
            i++;
            setTimeout(typeWriter, 100);
        }
    }
    
    setTimeout(typeWriter, 1000);
});