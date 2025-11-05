function createDialogBox(msg,format="ok") {
    var dbox = {};

    const overlay = document.createElement('div');
    const mbox = document.createElement('div');
    const bbox = document.createElement('div');
    const message = document.createElement('div');

    message.style.textAlign = "center";
    message.style.marginBottom = "5px";
    message.innerHTML = msg;
    mbox.className = 'message-box';
    mbox.appendChild(message);
    overlay.classList.add('basic-overlay','message-overlay','message-centered');
    bbox.classList.add('message-centered');
    mbox.appendChild(bbox);
    overlay.appendChild(mbox);
    document.body.appendChild(overlay);
    dbox.overlay = overlay;
    
    if (format == "yesno") {
        const yes = document.createElement('button');
        const no = document.createElement('button');
        yes.style.marginRight = "5px";
        yes.innerHTML = "Yes";
        no.innerHTML = "No";
        bbox.appendChild(yes);
        bbox.appendChild(no);
        dbox.yes = yes;
        dbox.no = no;
    } else if (format == "cancel") {
        const cancel = document.createElement('button');
        cancel.innerHTML = "Cancel";
        bbox.appendChild(cancel);
        dbox.cancel = cancel;
    } else if (format == "ok") {
        const ok = document.createElement('button');
        ok.innerHTML = "Ok";
        bbox.appendChild(ok);
        ok.addEventListener('click', function () {
            overlay.remove();
        })
        dbox.ok = ok;
    }
    return dbox;
}