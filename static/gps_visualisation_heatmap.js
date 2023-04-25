const USE_GEOJSON = true;
const CATEGORY = "tracking";
var legend = L.control({
    position: 'topright'
});
legend.onAdd = function(map) {
    this._div = L.DomUtil.create('div', 'info legend');
    this._div.innerHTML =
        '<div style="display: grid; grid-gap: 2px">' +
        '<div>Choose data</div><div><select id="trackSelect">' +
        '<optgroup label="Redis DB" id="redisOptions"></optgroup>' +
        '<optgroup label="Archive" id="archiveOptions"></optgroup>' +
        '</select></div>' +
        '<div><button onclick="loadTrackingData();">load data</button></div>' +
        '<div><button onclick="exportTrackingData();">export as JSON</button></div></div>';
        L.DomEvent.disableClickPropagation(this._div);
        return this._div;
};
legend.addTo(map);
var locations = [];
var heatmap = L.heatLayer(locations, {
    minOpacity: 0.5,
    maxZoom: 18,
    max: 1.0,
    radius: 10,
    blur: 15,
    gradient: null
});
heatmap.addTo(map);

function loadGeoJSON(fileName) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', fileName);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onload = function() {
        map.spin(false);
        if (xhr.status === 200) {
            locations = [];
            let geojson = JSON.parse(xhr.responseText);
            if (Array.isArray(geojson)) {
                geojson = geojson[0]
            }
            geojson.features.forEach(function(feature) {
                if (feature.geometry.type == "LineString") {
                    feature.geometry.coordinates.forEach(function(location) {
                        let lastEntry = locations[locations.length - 1];
                        if (lastEntry != undefined && lastEntry[0] == location[1] && lastEntry[1] == location[0]) {
                            // remove consecutive duplicate coordinates
                            return;
                        }
                        locations.push([location[1], location[0]]);
                    })
                } else if (feature.geometry.type == "Point") {
                    let location = feature.geometry.coordinates;
                    locations.push([location[1], location[0]]);
                }
            });
            heatmap.setLatLngs(locations);
            map.fitBounds(L.latLngBounds(locations));
        }
    };
    map.spin(true);
    xhr.send();
}

function loadTrackingData() {
    loadGeoJSON(document.getElementById("trackSelect").value);
}

function exportTrackingData() {
    let url = document.getElementById("trackSelect").value.replace(".geojson", ".json");
    let match = url.match(".*/(tracking.*.json)?.*$");
    if (match == null) {
        return;
    }
    let exportFileName = match[1];
    var xhr = new XMLHttpRequest();
    xhr.open('GET', url);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onload = function() {
        map.spin(false);
        if (xhr.status === 200) {
            var geojson = JSON.parse(xhr.responseText);
            let pom = document.createElement('a');
            pom.setAttribute('href', 'data:application/json;charset=utf-8,' + encodeURIComponent(xhr.responseText));
            pom.setAttribute('download', exportFileName);
            if (document.createEvent) {
                let event = document.createEvent('MouseEvents');
                event.initEvent('click', true, true);
                pom.dispatchEvent(event);
            } else {
                pom.click();
            }
        }
    };
    map.spin(true);
    xhr.send();
}
