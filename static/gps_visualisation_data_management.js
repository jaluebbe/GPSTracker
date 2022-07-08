function refreshTrackingIndex() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '../api/available_datasets?category=tracking');
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onload = function() {
        if (xhr.status === 200) {
            let trackSelect = document.getElementById('redisOptions');
            let len = trackSelect.children.length;
            for (var i=len; i; i--) {
                trackSelect.removeChild(i-1);
            }
            let trackingIndex = JSON.parse(xhr.responseText);
            trackingIndex.sort();
            for (var i=0; i < trackingIndex.length; i++) {
                let opt = document.createElement('option');
                if (USE_GEOJSON)
                    opt.value = '../api/dataset/' + trackingIndex[i] + '.geojson?from_archive=false';
                else
                    opt.value = '../api/dataset/' + trackingIndex[i] + '.json';
                let keyItems = trackingIndex[i].split('_');
                opt.text = keyItems[1] + ' ' + keyItems[2];
                trackSelect.appendChild(opt);
            }
        }
    };
    xhr.send();
}

function refreshArchiveIndex() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '../api/archived_datasets?category=tracking');
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onload = function() {
        if (xhr.status === 200) {
            let trackSelect = document.getElementById('archiveOptions');
            let len = trackSelect.children.length;
            for (var i=len; i; i--) {
                trackSelect.removeChild(i-1);
            }
            let trackingIndex = JSON.parse(xhr.responseText);
            trackingIndex.sort();
            for (var i=0; i < trackingIndex.length; i++) {
                let opt = document.createElement('option');
                if (USE_GEOJSON)
                    opt.value = '../api/dataset/' + trackingIndex[i] + '.geojson?from_archive=true';
                else
                    opt.value = '../archive/' + trackingIndex[i] + '.json';
                let keyItems = trackingIndex[i].split('_');
                opt.text = keyItems[1] + ' ' + keyItems[2];
                trackSelect.appendChild(opt);
            }
        }
    };
    xhr.send();
}

refreshTrackingIndex();
refreshArchiveIndex();
