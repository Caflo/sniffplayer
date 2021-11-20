// tasks.html
function remove_task(e) {
    var id = e.closest('tr').id;
    // check task is not started
    task_btn = e.previousElementSibling.getAttribute("class")
    if (task_btn !== 'btn btn-success') { 
        alert('You must first stop the task before deleting it!')
        return
    }
    var pos = $(e).parent().parent().index()
    xhttp = new XMLHttpRequest();

    var request = $.ajax({
        url: "/remove_task",
        type: "POST",
        data: {id : id},
        dataType: "html"
    });

    request.done(function(msg) {
        $("#task_table")[0].deleteRow(pos+1) // header of table doesn't count
        $("#errormsg")[0].innerHTML = ""
    });

    request.fail(function(jqXHR, textStatus) {
        $("#errormsg")[0].setAttribute("style", 'color: red;')
        $("#errormsg")[0].innerHTML = "<style='color:red;'>Something went wrong."
    });
}

function start_task(e) {
    var id = e.closest('tr').id;
    var pos = $(e).parent().parent().index()
    var buttons = e.parentElement.nextElementSibling.getElementsByTagName('button')
    xhttp = new XMLHttpRequest();

    var request = $.ajax({
        url: "/start_task",
        type: "POST",
        data: {id : id},
        dataType: "html"
    });

    request.done(function(msg) {
        e.setAttribute("class", "btn btn-danger")
        e.setAttribute("onclick", "stop_task(this)")
        e.innerHTML = '<i class="fa fa-stop"></i>'
        $("#errormsg")[0].innerHTML = ""
        buttons[0].disabled = true
        buttons[1].disabled = true
    });

    request.fail(function(jqXHR, textStatus) {
        $("#errormsg")[0].setAttribute("style", 'color: red;')
        $("#errormsg")[0].innerHTML = "<style='color:red;'>Something went wrong."
    });
}

function stop_task(e) {
    var id = e.closest('tr').id;
    var pos = $(e).parent().parent().index()
    xhttp = new XMLHttpRequest();

    var request = $.ajax({
        url: "/stop_task",
        type: "POST",
        data: {id : id},
        dataType: "html"
    });

    request.done(function(msg) {
        e.setAttribute("class", "btn btn-success")
        e.setAttribute("onclick", "start_task(this)")
        var buttons = e.parentElement.nextElementSibling.getElementsByTagName('button')
        e.innerHTML = '<i class="fa fa-play"></i>'
        $("#errormsg")[0].setAttribute("style", 'color: black;')
        $("#errormsg")[0].innerHTML = "Pcap file \"task_"+id+".pcap\" saved."
        buttons[0].disabled = false
        buttons[1].disabled = false
    });

    request.fail(function(jqXHR, textStatus) {
        $("#errormsg")[0].setAttribute("style", 'color: red;')
        $("#errormsg")[0].innerHTML = "Something went wrong."
    });
}

function schedule_task(e) {
    var id = e.closest('tr').id;
    var pos = $(e).parent().parent().index()
    xhttp = new XMLHttpRequest();

    var request = $.ajax({
        url: "/schedule_task",
        type: "POST",
        data: {id : id},
        dataType: "html"
    });

    request.done(function(msg) {
        $("#errormsg")[0].setAttribute("style", 'color: black;')
        $("#errormsg")[0].innerHTML = "sniffer "+id+" scheduled to start" // TODO modify
        buttons[0].disabled = true
    });

    request.fail(function(jqXHR, textStatus) {
        $("#errormsg")[0].setAttribute("style", 'color: red;')
        $("#errormsg")[0].innerHTML = "<style='color:red;'><i>Something went wrong.</i>"
    });
}


function remvove_schedule(e) {
    var id = e.closest('tr').id;
    var pos = $(e).parent().parent().index()
    xhttp = new XMLHttpRequest();

    var request = $.ajax({
        url: "/remove_schedule",
        type: "POST",
        data: {id : id},
        dataType: "html"
    });

    request.done(function(msg) {
        $("#errormsg")[0].innerHTML = ""
        buttons[0].disabled = true
    });

    request.fail(function(jqXHR, textStatus) {
        $("#errormsg")[0].setAttribute("style", 'color: red;')
        $("#errormsg")[0].innerHTML = "<style='color:red;'><i>Something went wrong.</i>"
    });

}

// maybe i don't need those
$('#sel_iface').on('click',function() {
    iface = $(this).val();
});

$('#sel_sniff_mode').on('click',function() {
    sniff_mode = $(this).val();
});