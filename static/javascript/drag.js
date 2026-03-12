document.addEventListener("DOMContentLoaded", () => {
const boxText = document.getElementById("text1")
const boxes = document.getElementsByClassName("box")
boxText.addEventListener('dragstart',dragStart)
boxText.addEventListener('dragend',dragEnd)

for(let box of boxes)
{
    box.addEventListener('dragover',dragOver);
    box.addEventListener('dragenter',dragEnter);
    box.addEventListener('dragleave',dragLeave);
    box.addEventListener('drop',Drop);
}
function dragStart()
{
   setTimeout(()=>(this.className= 'invisible'),0);
}

function dragEnd()
{
    this.className = 'boxText';
}

function dragOver(e)
{
    e.preventDefault();
}

function dragEnter(e)
{
    e.preventDefault();
}

function dragLeave(e)
{
    e.preventDefault();
}

function Drop()
{
    this.className = 'box';
    this.append(boxText);
}
});