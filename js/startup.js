
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
        //return server_url + '/panorama-demo/video-snippets/' + video_name + '_' + start_time + '.mp4'
        return 'http://elmo.csail.mit.edu/panorama-demo/videos/' + video_name + '.mp4#t=' + start_time

}


function relevant_finished_loading(i, relevant_video_num, query_str) {
    console.log('finished_loading:' + i + ' finished:' + RELEVANT_LOADED_VIDEO_COUNT);
    RELEVANT_LOADED_VIDEO_COUNT += 1;
    //console.log(RELEVANT_LOADED_VIDEO_COUNT);
    //console.log(relevant_video_num);
    if (RELEVANT_LOADED_VIDEO_COUNT == relevant_video_num) {
        console.log('finished loading relevant videos');
        relevant_start_play(relevant_video_num, query_str);
    }
}

function irrelevant_finished_loading(i, irrelevant_video_num) {
    IRRELEVANT_LOADED_VIDEO_COUNT += 1;
    if (IRRELEVANT_LOADED_VIDEO_COUNT == irrelevant_video_num) {
        console.log('finished loading irrelevant videos');
        irrelevant_start_play(irrelevant_video_num);
    }
}

function irrelevant_start_play(irrelevant_video_num) {

    var w = window.innerWidth;    
    var h_step = 216; 
    var region_div = document.getElementById('unmatched_video_region');
    region_div.style.marginLeft = w * 11.5/24.0; 
    region_div.style.width = w * 10/24.0;
    region_div.style.border = "5px solid lightgray";
    region_div.style.borderRadius = "13px";
    region_div.style.padding = "45px 15px 15px";
    region_div.style.height = irrelevant_video_num * h_step + 20;  
    region_div.style.visibility = 'visible';  

    var video_region_pos = $('#unmatched_video_region').offset();
    var unmatched_region_text_div = document.getElementById('unmatched_video_text_region');
    unmatched_region_text_div.innerHTML = '&nbsp;Irrelevant videos&nbsp;';
    unmatched_region_text_div.style.visibility = 'visible';

    var w = window.innerWidth;    
    w = w - 20;
    var w_step = 300; 
    var h_step = 216; 
    var w_size =  parseInt(w/w_step);
    for (i = 0; i < irrelevant_video_num;  ++i) { 
        var top_pos = 60 + h_step * i; 
        var left_pos = video_region_pos['left'] + 80;
        var d = document.getElementById('irrelevant-' + i);
        d.style.position = "absolute";
        d.style.visibility = "visible";
        d.style.top = top_pos;
        d.style.left = left_pos;  
        //var v = document.getElementById('irrelevant_video-' + i);  
        //v.pause();
    }
}

function relevant_start_play(relevant_video_num, query_str) {

    var w = window.innerWidth;    
    var h_step = 216; 
    var matched_region_div = document.getElementById('matched_video_region');
    matched_region_div.style.left = w * 4.5/24.0; 
    matched_region_div.style.width = w * 10/24.0;
    matched_region_div.style.border = "5px solid lightgray";
    matched_region_div.style.borderRadius = "13px";
    matched_region_div.style.padding = "45px 15px 15px";
    matched_region_div.style.height = relevant_video_num * h_step + 20;  
    matched_region_div.style.visibility = 'visible';  
   
  
    var video_region_pos = $('#matched_video_region').offset();
    document.getElementById('loading').style.visibility = 'hidden';

    var matched_region_text_div = document.getElementById('matched_video_text_region');
    if (relevant_video_num > 0) { 
        matched_region_text_div.innerHTML = '&nbsp;Videos relevant to "' + query_str + '"&nbsp;';
        matched_region_text_div.style.visibility = 'visible';
    }

    w = w - 20;
    var w_step = 300; 
    var h_step = 216; 
    var w_size =  parseInt(w/w_step);
    for (i = 0; i < relevant_video_num;  ++i) { 
        var top_pos = 60 + h_step * i; 
        var left_pos = video_region_pos['left'] + 80;
        var d = document.getElementById('relevant-' + i);
        d.style.position = "absolute";
        d.style.visibility = "visible";
        d.style.top = top_pos;
        d.style.left = left_pos;  
        //var v = document.getElementById('relevant_video-' + i);  
        //v.pause();
    }
}

function playRelevantVideo(i) {
    var v = document.getElementById('relevant_video-' + i);  
    v.play();
}

function pauseRelevantVideo(i) {
    var v = document.getElementById('relevant_video-' + i);  
    v.pause();
}


function playIrrelevantVideo(i) {
    var v = document.getElementById('irrelevant_video-' + i);  
    v.play();
}

function pauseIrrelevantVideo(i) {
    var v = document.getElementById('irrelevant_video-' + i);  
    v.pause();
}



function showVideos(query_str, relevant_dict, irrelevant_dict) {

    var relevant_video_num = Math.min(relevant_dict.length, NUM_RELEVANT_VIDEOS);
    var irrelevant_video_num = Math.min(irrelevant_dict.length, NUM_IRRELEVANT_VIDEOS);
    RELEVANT_LOADED_VIDEO_COUNT = 0;
    IRRELEVANT_LOADED_VIDEO_COUNT = 0;
              
    var w = window.innerWidth;    
    w = w - 20;
    var w_step = 300; 
    var h_step = 216; 
    var w_size =  parseInt(w/w_step);
    var video_w = w_step - 10;
    var video_h = h_step - 10;

	document.getElementById('loading').style.visibility = 'visible';
    /** Create div for each video and start load each video**/
    var html_str = ''; 
    var matched_region_text_div = document.getElementById('matched_video_text_region');
    if (relevant_video_num == 0) { 
        matched_region_text_div.innerHTML = '&nbsp;No videos matching "' + query_str +'"&nbsp;' ;
        matched_region_text_div.style.visibility = 'visible';
	    document.getElementById('loading').style.visibility = 'hidden';
    }
    for (i = 0;  i < relevant_video_num ; ++i) {

        //html_str  += '<div id="relevant-' + i + '" style="position:absolute;  visibility:hidden;">' + '<video id="relevant_video-' +i + '" width="' + video_w + '" height="'+ video_h +'" controls muted preload="auto" autostart="false" oncanplay="relevant_finished_loading(' + i + ',' + relevant_video_num  + ', \'' + query_str +  '\')"  onmouseover="playRelevantVideo(' + i + ')"  onmouseout="pauseRelevantVideo(' + i + ')"> <source src ="' + getVideoURL(relevant_dict[i]['video_name'], relevant_dict[i]['start'], relevant_dict[i]['end']) + '" type="video/mp4"></video> </div>';
        html_str  += '<div id="relevant-' + i + '" style="position:absolute;  visibility:hidden;">' + '<video id="relevant_video-' +i + '" width="' + video_w + '" height="'+ video_h +'" controls muted preload="auto" autostart="false" oncanplay="relevant_finished_loading(' + i + ',' + relevant_video_num  + ', \'' + query_str +  '\')"  onmouseover="playRelevantVideo(' + i + ')"  onmouseout="pauseRelevantVideo(' + i + ')"> <source src ="' + relevant_dict[i]['video_url'] + '" type="video/mp4"></video> </div>';
    } 

	$('#matched_video_region').html(html_str);

    var html_str = '';
    for (i = 0; i < irrelevant_video_num && relevant_video_num > 0; ++i) {

        html_str  += '<div id="irrelevant-' + i + '" style="position:absolute;  visibility:hidden;">' + '<video id="irrelevant_video-' +i + '" width="' + video_w + '" height="'+ video_h +'" controls muted preload="auto" autostart="false" oncanplay="irrelevant_finished_loading(' + i + ',' + irrelevant_video_num  + ')"  onmouseover="playIrrelevantVideo(' + i + ')"  onmouseout="pauseIrrelevantVideo(' + i + ')"> <source src ="' + getVideoURL(irrelevant_dict[i]['video_name'], irrelevant_dict[i]['start'], irrelevant_dict[i]['end']) + '" type="video/mp4"></video> </div>';

    } 
    $('#unmatched_video_region').html(html_str);

}

function reset(){
    window.location.reload();
}

function loadPreviewVideos(responseText){

    var response_obj = JSON.parse(responseText); 
    var irrelevant_dict = response_obj['response']['irrelevant'];
    var relevant_dict = response_obj['response']['relevant'];

    var relevant_video_num = relevant_dict.length;
    var irrelevant_video_num = irrelevant_dict.length;

    var video_region_pos = $('#preview_video_region').offset();
    var w = $('#preview_video_region').width();    
    w = w - 30;
    var w_step = 300; 
    var h_step = 216; 
    //var w_size = parseInt(w/w_step);
    var w_size = 3;
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
        var left_pos = w * 0.15 + w_step * col;
        html_str  += '<div id="preview-' + i + '" style="position:absolute; top:' + top_pos + '; left:'+ left_pos +';">' + '<video id="preview_video-' +i + '" width="' + video_w + '" height="'+ video_h +'" controls muted preload="auto" autostart="false""> <source src ="' + getVideoURL(video_obj['video_name'], video_obj['start'], video_obj['start'] + 3) + '" type="video/mp4"></video> </div>';
        i += 1;
        selected_videos.push(video_obj['video_name']);
    } 
	$('#preview_video_region').html(html_str);
    
}

function processResponse(query_str, responseText){

    console.log(responseText);
    var response_obj = JSON.parse(responseText); 
    var irrelevant_dict = response_obj['response']['irrelevant'];
    var relevant_dict = response_obj['response']['relevant'];
    showVideos(query_str, relevant_dict, irrelevant_dict); 

}

function doSearch(){

    var query_str = document.getElementById('searchbox').value;
    document.getElementById('matched_video_text_region').style.visibility = 'hidden';
    document.getElementById('matched_video_region').style.visibility = 'hidden';
    document.getElementById('unmatched_video_text_region').style.visibility = 'hidden';
    document.getElementById('unmatched_video_region').style.visibility = 'hidden';
	$('#loading').html('Searching live streams...');
    $('#preview_video_region').html('');
    IRRELEVANT_LOADED_VIDEO_COUNT = 0;
    RELEVANT_LOADED_VIDEO_COUNT = 0;
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
                    processResponse(query_str, xml_http.responseText);
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


