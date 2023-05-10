var map = L.map('map', {
    minZoom: 0,
    maxZoom: 19
});
map.setView([49.0, 9.0], 7);
//map.attributionControl.addAttribution(
//    '<a href="https://github.com/jaluebbe/GPSTracker">Source on GitHub</a>');
// add link to privacy statement
//map.attributionControl.addAttribution(
//    '<a href="static/datenschutz.html" target="_blank">Datenschutzerkl&auml;rung</a>');
function addOSMVectorLayer(styleName, layerLabel) {
    let myLayer = L.maplibreGL({
        style: styleName + '.json',
        attribution: '&copy; <a href="https://openmaptiles.org/">OpenMapTiles</a>, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    });
    layerControl.addBaseLayer(myLayer, layerLabel);
    // make sure to reprint the vector map after being selected.
    map.on('baselayerchange', function(eo) {
        if (eo.name === layerLabel) {
            myLayer._update();
        }
    });
    return myLayer;
};
L.control.scale({
    'imperial': false
}).addTo(map);
var layerControl = L.control.layers({}, {}, {
    collapsed: L.Browser.mobile, // hide on mobile devices
    position: 'topright'
}).addTo(map);
addOSMVectorLayer("/api/vector/style/osm_basic", "OSM Basic (offline)").addTo(map);
addOSMVectorLayer("/api/vector/style/osm_liberty", "OSM Liberty (offline)");
