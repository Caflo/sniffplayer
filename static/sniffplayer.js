// tasks.html

function add_task() {

}

function remove_task(e) {
    var id = $(e).closest('tr')[0].id;

    xhttp = new XMLHttpRequest()
    xhttp.open("POST", "/remove_task");
    xhttp.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    xhttp.send("id="+id);
    var url = '/tasks'
    window.location = url;

//    alert(currentRow.id);
}

function start_sniffer() {

}

function stop_sniffer() {

}

$('#sel_iface').on('click',function() {
//    console.log($(this).val());
    iface = $(this).val();
});

$('#sel_sniff_mode').on('click',function() {
//    console.log($(this).val());
    sniff_mode = $(this).val();
});

