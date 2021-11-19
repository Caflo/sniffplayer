// tasks.html
function remove_task(e) {
    var id = e.closest('tr').id;
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
        $("#errormsg")[0].innerHTML = "Something went wrong"
    });
}

function start_task(e) {
    var id = e.closest('tr').id;
    var pos = $(e).parent().parent().index()
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
    });

    request.fail(function(jqXHR, textStatus) {
        $("#errormsg")[0].innerHTML = "Something went wrong."
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
        e.innerHTML = '<i class="fa fa-play"></i>'
        $("#errormsg")[0].innerHTML = "Pcap file \"task_"+id+".pcap\" saved."
    });

    request.fail(function(jqXHR, textStatus) {
        $("#errormsg")[0].innerHTML = "Something went wrong."
    });
}

$('#sel_iface').on('click',function() {
    iface = $(this).val();
});

$('#sel_sniff_mode').on('click',function() {
    sniff_mode = $(this).val();
});


// files.html