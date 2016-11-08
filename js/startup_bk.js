
// entry point
function StartPanorama() {

	console.time('startup');

	setPageFormat();
		
	console.timeEnd('startup');
};

// Using parameters in page var to set up the webpage format
function setPageFormat(){
		
		// Put image and choice side-by-side
		//$('#main_canvas').append("<div id = 'loading'> Searching live streams...</div>" +
		//						 "<div id = 'video_region'> </div>" +
		//						 "<br> </br> "  
		//						);
			
		$('#main_canvas').width('100%');
		document.getElementById('loading').style.visibility = 'hidden';

};


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
    //clearInterval(timer);
}


function finished_loading(i) {
    console.log('finished_loading:' + i);
    relevant_loaded_video_count += 1;
    console.log(relevant_loaded_video_count);
    console.log(relevant_video_num);
    if (relevant_loaded_video_count == relevant_video_num) {
        relevant_finished_loading = 1;
        start_delayed_play();
    }
}

function showVideos(relevant_dict, irrelevant_dict) {
    relevant_video_num = relevant_dict.length;
    irrelevant_video_num = irrelevant_dict.length;
    relevant_loaded_video_count = 0;
    relevant_finished_loading = 0;
    relevant_start_videos = [];
    for (i = 0; i < relevant_video_num; ++i){
        obj = relevant_dict[i];
        relevant_start_videos[i] = 0;
    }

              
    var w = window.innerWidth;    
    w = w - 20;
    w_step = 500; 
    h_step = 360; 
    w_size =  parseInt(w/w_step);
    video_w = w_step - 10;
    video_h = h_step - 10;

    /** Create div for each video and start load each video**/
    var html_str = '';

    for (i = 0; i < relevant_video_num; ++i) {

       html_str  += '<div id="relevant-' + i + '" style="position:absolute;  visibility:hidden;">' + '<video id="relevant_video-' +i + '" width="' + video_w + '" height="'+ video_h +'" controls muted preload="auto" autostart="false" oncanplay="finished_loading(' + i + ')"> <source src ="' + getVideoURL(relevant_dict[i]['video_name'], relevant_dict[i]['start'], relevant_dict[i]['end']) + '" type="video/mp4"></video> </div>';

    } 

	document.getElementById('loading').style.visibility = 'visible';
	$('#matched_video_region').html(html_str);

}

function reset(){
    window.location.reload();
}

function processResponse(responseText){
    console.log(responseText);
    var response_obj = JSON.parse(responseText); 
    irrelevant_dict = response_obj['response']['irrelevant'];
    relevant_dict = response_obj['response']['relevant'];
    showVideos(relevant_dict, irrelevant_dict); 
}

function doSearch(){
    query_str = document.getElementById('searchbox').value;
     $('#panorama').html('Panorama -- ' + query_str); 
	 $('#loading').html('Searching live streams...');
    
    if (window.XMLHttpRequest) {
        var xml_http = new XMLHttpRequest();
        xml_http.onreadystatechange = function (){

            if (xml_http.readyState == 4 && xml_http.status == 200) {
                
                processResponse(xml_http.responseText);
    	        document.getElementById('loading').style.visibility = 'hidden';
            } else if (xml_http.readyState == 4 && xml_http.status == 500){
				  $('#loading').html('Visual search does not support "' + query_str + '". Try query starting with "guitar,A person, dog, cat, car"');
				}

        };
        xml_http.open("GET", server_url + ':5000/redis-search?query=' + query_str, true);
        xml_http.setRequestHeader("Access-Control-Allow-Origin", '*');
        xml_http.send('');
	    document.getElementById('loading').style.visibility = 'visible';
    } 
} 



function setSubmitButtonVisibility(){
	console.log(selected_value);
	console.log(video_finished_a);
	console.log(video_finished_b);
	
	if (selected_value != null && video_finished_a && video_finished_b) {
			document.getElementById("mt_submit").disabled = false;
	}else{
			if (video_finished_a == false || video_finished_b == false) {
				$("#mt_submit").text('Submit HIT (Please finish watching the videos)');
			}
			document.getElementById("mt_submit").disabled = true;
	}
};
