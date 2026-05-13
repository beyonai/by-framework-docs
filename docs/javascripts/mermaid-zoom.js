// Event delegation for Mermaid diagram zoom
document.addEventListener("click", function(e) {
    // Find closest .mermaid element
    const mermaid = e.target.closest(".mermaid");
    if (mermaid) {
        // Toggle the fullscreen class
        mermaid.classList.toggle("fullscreen");
        
        // Prevent body scrolling when a diagram is in fullscreen
        if (mermaid.classList.contains("fullscreen")) {
            document.body.style.overflow = "hidden";
        } else {
            document.body.style.overflow = "";
        }
    }
});
