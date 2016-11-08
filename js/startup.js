
// entry point
function StartPanorama() {

	console.time('startup');
	setPageFormat();
    startPreview();
	console.timeEnd('startup');
};

// Using parameters in page var to set up the webpage format
function setPageFormat(){
		
		$('#main_canvas').width('100%');
		document.getElementById('loading').style.visibility = 'hidden';
};

function startPreview(){
        // randomly start previewing some videos        
        postSearch('dog', 1);        
 
}

function getVideoURL(video_name, start_time, end_time) {
        return server_url + '/panorama-demo/videos/' + video_name + '.mp4#t=' + start_time
}


function play_video(relevant_start_videos, new_video_idx) {

    var video_region_pos = $('#matched_video_region').offset();
  
    var j = 0;

    for (var m = 0; m < relevant_video_num; ++m) {
     
        if (relevant_start_videos[m] > 0 || m == new_video_idx) {
            row = parseInt(j/w_size);
            col = parseInt(j%w_size);
            var d = document.getElementById('relevant-' + m);
            d.style.position = "absolute";
            d.style.visibility = "visible";
            d.style.top = video_region_pos['top'] + h_step * row;
            d.style.left = 20 + w_step * col;  
            j += 1;

        }else if (relevant_start_videos[m] < 0) {

            var d = document.getElementById('relevant-' + m);
            d.style.position = "absolute";
            d.style.visibility = "hidden";
            var v = document.getElementById('relevant_video-' + m);  
            v.pause();
        }

        if (m == new_video_idx) { 
            var v = document.getElementById('relevant_video-' + m);  
            v.play();
        }

    }
}

function start_delayed_play() {
    console.log('start play');
    var timer = setInterval(refresh, 1000);
    var d = new Date();
    var start_time = d.getTime();
    function refresh() {
        console.log('refresh');
        console.log(relevant_start_videos);
        var d = new Date();
        var curtime = d.getTime();
        var elapsed_time_s = (curtime - start_time)/1000;
        for (var k = 0; k < relevant_video_num; ++k){
          
            var video_play_time = (curtime - relevant_start_videos[k])/1000;
            var video_duration = relevant_dict[k]['end'] - relevant_dict[k]['start'];
            console.log(video_play_time);
            if (relevant_start_videos[k] > 0 && video_duration < video_play_time) {
                relevant_start_videos[k] = -1;
                play_video(relevant_start_videos, -1);
            }

            if (relevant_start_videos[k] == 0 && relevant_dict[k]['delay'] < elapsed_time_s) {
                play_video(relevant_start_videos, k);
                relevant_start_videos[k] = curtime;
            }

        }
    }
}

function finished_loading(i, relevant_video_num) {
    console.log('finished_loading:' + i);
    RELEVANT_LOADED_VIDEO_COUNT += 1;
    console.log(RELEVANT_LOADED_VIDEO_COUNT);
    console.log(relevant_video_num);
    if (RELEVANT_LOADED_VIDEO_COUNT == relevant_video_num) {
        start_play(relevant_video_num);
    }
}
function start_play(relevant_video_num) {
    var video_region_pos = $('#matched_video_region').offset();
    document.getElementById('loading').style.visibility = 'hidden';

    var w = window.innerWidth;    
    w = w - 20;
    var w_step = 300; 
    var h_step = 216; 
    var w_size =  parseInt(w/w_step);
    for (i = 0; i < relevant_video_num;  ++i) { 
        var row = parseInt(i/w_size);
        var col = parseInt(i%w_size);
        var top_pos = video_region_pos['top'] + h_step * row; 
        var left_pos = 120 + w_step * col;
        var d = document.getElementById('relevant-' + i);
        d.style.position = "absolute";
        d.style.visibility = "visible";
        d.style.top = top_pos;
        d.style.left = left_pos;  
        var v = document.getElementById('relevant_video-' + i);  
        v.play();
    }
}

function showVideos(relevant_dict, irrelevant_dict) {

    var relevant_video_num = Math.min(relevant_dict.length, NUM_RELEVANT_VIDEOS);
    var irrelevant_video_num = Math.min(irrelevant_dict.length, NUM_IRRELEVANT_VIDEOS);
    RELEVANT_LOADED_VIDEO_COUNT = 0;

              
    var w = window.innerWidth;    
    w = w - 20;
    var w_step = 300; 
    var h_step = 216; 
    var w_size =  parseInt(w/w_step);
    var video_w = w_step - 10;
    var video_h = h_step - 10;

    /** Create div for each video and start load each video**/
    var html_str = '';

    for (i = 0;  i < relevant_video_num ; ++i) {

        html_str  += '<div id="relevant-' + i + '" style="position:absolute;  visibility:hidden;">' + '<video id="relevant_video-' +i + '" width="' + video_w + '" height="'+ video_h +'" controls muted preload="auto" autostart="false" oncanplay="finished_loading(' + i + ',' + relevant_video_num  + ')"> <source src ="' + getVideoURL(relevant_dict[i]['video_name'], relevant_dict[i]['start'], relevant_dict[i]['end']) + '" type="video/mp4"></video> </div>';

    } 
	document.getElementById('loading').style.visibility = 'visible';
	$('#matched_video_region').html(html_str);

    var html_str = '';

    for (i = 0;  i < irrelevant_video_num ; ++i) {

        html_str  += '<div id="relevant-' + i + '" style="position:absolute;  visibility:hidden;">' + '<video id="relevant_video-' +i + '" width="' + video_w + '" height="'+ video_h +'" controls muted preload="auto" autostart="false" oncanplay="finished_loading(' + i + ',' + relevant_video_num  + ')"> <source src ="' + getVideoURL(relevant_dict[i]['video_name'], relevant_dict[i]['start'], relevant_dict[i]['end']) + '" type="video/mp4"></video> </div>';

    } 
	document.getElementById('loading').style.visibility = 'visible';
	$('#matched_video_region').html(html_str);
}

function reset(){
    window.location.reload();
}

function loadPreviewVideos(responseText){

    console.log(responseText);
    var response_obj = JSON.parse(responseText); 
    var irrelevant_dict = response_obj['response']['irrelevant'];
    var relevant_dict = response_obj['response']['relevant'];

    var relevant_video_num = relevant_dict.length;
    var irrelevant_video_num = irrelevant_dict.length;

    var video_region_pos = $('#preview_video_region').offset();
    var w = window.innerWidth;    
    w = w - 20;
    var w_step = 300; 
    var h_step = 216; 
    var w_size = parseInt(w/w_step);
    var video_w = w_step - 10;
    var video_h = h_step - 10;

    var html_str = '';
    var selected_videos = [];
    var i = 0;
    var relevant_idx = 0;
    var irrelevant_idx = 0;
    while (selected_videos.length < NUM_PREVIEW_VIDEOS) { 
        // from relevant or irrelevant
        var video_obj = null; 
        if (Math.random() < 0.3) {
            if (relevant_idx < relevant_video_num) { // relevant
                video_obj = relevant_dict[relevant_idx];
                relevant_idx += 1;
            } else {
                continue;
            }
        } else {
            if (irrelevant_idx < irrelevant_video_num) {
                video_obj = irrelevant_dict[irrelevant_idx];
                irrelevant_idx += 1;
            } else {
                continue;
            }
        }
       
        var row = parseInt(i/w_size);
        var col = parseInt(i%w_size);
        var top_pos = video_region_pos['top'] + h_step * row; 
        var left_pos = 120 + w_step * col;
        html_str  += '<div id="preview-' + i + '" style="position:absolute; top:' + top_pos + '; left:'+ left_pos +';">' + '<video id="preview_video-' +i + '" width="' + video_w + '" height="'+ video_h +'" controls muted preload="auto" autostart="false""> <source src ="' + getVideoURL(video_obj['video_name'], video_obj['start'], video_obj['start'] + 3) + '" type="video/mp4"></video> </div>';
        i += 1;
        selected_videos.push(video_obj['video_name']);
    } 
	$('#preview_video_region').html(html_str);
    
}

function processResponse(responseText){

    console.log(responseText);
    var response_obj = JSON.parse(responseText); 
    var irrelevant_dict = response_obj['response']['irrelevant'];
    var relevant_dict = response_obj['response']['relevant'];
    showVideos(relevant_dict, irrelevant_dict); 

}

function doSearch(){

    query_str = document.getElementById('searchbox').value;
    $('#panorama').html('Panorama -- ' + query_str); 
	$('#loading').html('Searching live streams...');
    $('#preview_video_region').html('');
    postSearch(query_str, 0);

}
function postSearch(query_str, isPreview = 1) {    

    if (window.XMLHttpRequest) {
        var xml_http = new XMLHttpRequest();
        xml_http.onreadystatechange = function (){

            if (xml_http.readyState == 4 && xml_http.status == 200) {
               
        	    document.getElementById('loading').style.visibility = 'hidden';
                if (isPreview == 1) {
                    loadPreviewVideos(xml_http.responseText); 
                } else if (isPreview == 0) {
                    processResponse(xml_http.responseText);
                }
            } else if (xml_http.readyState == 4 && xml_http.status == 500){

                $('#loading').html('500 Internal Error');
				  //$('#loading').html('Visual search does not support "' + query_str + '". Try query starting with "guitar,A person, dog, cat, car"');
				}
        };
        if (isPreview == 1) {
            xml_http.open("GET", server_url + ':5000/redis-search?query=' + query_str + '&option=Length', true);
        } else { 
            xml_http.open("GET", server_url + ':5000/redis-search?query=' + query_str + '&option=Default', true);
	        document.getElementById('loading').style.visibility = 'visible';
        }
        xml_http.setRequestHeader("Access-Control-Allow-Origin", '*');
        xml_http.send('');
    } 
} 


