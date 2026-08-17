document.addEventListener("DOMContentLoaded", () => {
  const draggables = document.querySelectorAll(".boxText"); // select ALL draggables
  const boxes = document.getElementsByClassName("box");
  let draggedItem = null; // track whichever element is being dragged

  for (let draggable of draggables) {
    draggable.addEventListener("dragstart", dragStart);
    draggable.addEventListener("dragend", dragEnd);
  }

  for (let box of boxes) {
    box.addEventListener("dragover", dragOver);
    box.addEventListener("dragenter", dragEnter);
    box.addEventListener("dragleave", dragLeave);
    box.addEventListener("drop", Drop);
  }

  function dragStart() {
    draggedItem = this; // remember which element is being dragged
    setTimeout(() => (this.className = "invisible"), 0);
  }

  function dragEnd() {
    this.className = "boxText";
    draggedItem = null;
  }

  function dragOver(e) {
    e.preventDefault();
  }

  function dragEnter(e) {
    e.preventDefault();
  }

  function dragLeave(e) {
    e.preventDefault();
  }

function Drop(e) {
    e.preventDefault();
    if (this.children.length === 0 || this.contains(draggedItem)) {
      this.append(draggedItem);
    } else {
      console.log("This box is already full!");
    }
  }
});