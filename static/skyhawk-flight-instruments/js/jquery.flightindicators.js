/* 
Skyhawk Flight Instruments (https://github.com/uw-ray/Skyhawk-Flight-Instruments)
By Raymond Blaga (raymond.blaga@gmail.com), Edward Hanna (edward.hanna@senecacollege.ca), Pavlo Kuzhel (pavlo.kuzhel@senecacollege.ca)

Forked from jQuery Flight Indicators (https://github.com/sebmatton/jQuery-Flight-Indicators)
By Sébastien Matton (seb_matton@hotmail.com)

Published under GPLv3 License.
*/

(function($) {

    "use strict";

    function FlightIndicator( placeholder, type, options ) {

        var built = true,
        settings = $.extend({
            size : 400,
            showBox : true,
            showScrews : true,
            showIndicatorInner : true,
            airspeed : 0,
            trueairspeed: 0,
            roll : 0,
            pitch : 0,
            off_flag: true,
            ils: true,
            ils_localizer: 0,
            ils_glideslope: 0,
            altitude : 0,
            pressure : 30,
            turn : 0,
            slip : 0.5,
            heading : 0,
            beaconone : 90,
            beacononeshow : false,
            beacontwo : 30,
            beacontwoshow : false,
            vario : 0,
            img_directory : 'img/'
            }, options 
        ),
        constants = {
            pitch_bound: 26
        }

        // Air Speed - Set air speed
        function _setAirSpeed(speed){

            var deg = 0;

            if (speed >= 0 && speed < 40) deg = speed * 0.9;
            if (speed >= 40 && speed <= 160) deg = speed * 1.8 - 36;
            if (speed > 70 && speed <= 160) deg = speed * 2 - 50;
            if (speed > 160) deg = speed + 110;
            if (speed > 200) deg = 311 + (speed % 2);

            placeholder.each(function(){
                $(this).find('div.instrument.airspeed div.airspeed')
                    .css('transform', 'rotate(' + deg + 'deg)');
                    
            });    

        }

        // Air Speed - Set true air speed
        function _setTrueAirSpeed(speed){
            // Make me work!
        }

        // Attitude - Set pitch
        function _setPitch(pitch){
            if(pitch>constants.pitch_bound) pitch = constants.pitch_bound;
            else if(pitch<-constants.pitch_bound) pitch = -constants.pitch_bound;
            placeholder.each(function(){
                $(this).find('div.instrument.attitude div.attitude div.attitude_pitch').css('transform', 'translateY(' + (pitch * 0.7) + '%)');
            });
        }

        // Attitude - Set roll
        function _setRoll(roll){
            placeholder.each(function(){
                $(this).find('div.instrument.attitude div.attitude').css('transform', 'rotate('+ roll +'deg)');
            });
        }

        // Attitude - Set visibility of the off flag
        function _setOffFlag(visible){
            placeholder.each(function(){
                $(this).find('div.instrument.attitude div.attitude_off_flag').toggle(visible);
            });
        }

        // Attitude - Instrument landing system - Set visibility
        function _setILS(visible){
        	placeholder.each(function(){
        		$(this).find('div.instrument.attitude div.attitude_ils').toggle(visible);
        	});
        }

		// Attitude - Instrument landing system - Set localizer angle
        function _setILSLocalizer(angle){

        	var ang = (Math.abs(angle) > 14.5) ? (Math.abs(angle) / angle) * 14.5 : angle;

        	placeholder.each(function(){
        		$(this).find('div.instrument.attitude div.attitude_ils_localizer').css({
        			'transform': 'rotate(' + ang + 'deg)',
        			'transform-origin': 'center top'
        		});
        	});
        }

		// Attitude - Instrument landing system - Set glideslope angle
        function _setILSGlideslope(angle){

        	var ang = (Math.abs(angle) > 14.5) ? (Math.abs(angle) / angle) * 14.5 : angle;

        	placeholder.each(function(){
        		$(this).find('div.instrument.attitude div.attitude_ils_glideslope').css({
        			'transform': 'rotate(' + ang + 'deg)',
        			'transform-origin': 'center left'
        		});
        	});
        }

        // Altimeter - Set altitude
        function _setAltitude(altitude){
            var hand100 = altitude / 1000 * 360;
            var hand1000 = altitude / 10000 * 360;
            var hand10000 = altitude / 100000 * 360;
            placeholder.each(function(){
                $(this).find('div.instrument.altimeter div.altimeter_hand100').css('transform', 'rotate(' + hand100 + 'deg)');
                $(this).find('div.instrument.altimeter div.altimeter_hand1000').css('transform', 'rotate(' + hand1000 + 'deg)');
                $(this).find('div.instrument.altimeter div.altimeter_hand10000').css('transform', 'rotate(' + hand10000 + 'deg)');
            });    
        }

        // Altimeter - Set pressure (by default inHg; set milibar to true if you wish to use mbar)
        function _setPressure(pressure, milibar){

            var pressure1 = 0, pressure2 = 0;
            // pressure1: 5 units = 9 degrees
            // pressure2: 0.1 units = 6 degrees

            if (milibar !== true) {
                if (pressure >= 27.1 && pressure <= 33) {
                    pressure1 = (925 - 33.8639 * pressure) * 1.8;
                    pressure2 = (pressure - 27.1) * 60;
                }
            } else {
                if (pressure >= 925 && pressure <= 1120) {
                    pressure1 = (925 - pressure) * 1.8;
                    pressure2 = (pressure * 0.0295300 - 27.1) * 60;
                }
            }

            placeholder.each(function(){
                $(this).find('div.instrument.altimeter div.altimeter_pressurembar').css('transform', 'rotate(' + pressure1 + 'deg)');
            });    
            placeholder.each(function(){
                $(this).find('div.instrument.altimeter div.altimeter_pressureinhg').css('transform', 'rotate(' + -pressure2 + 'deg)');
            });            

        }

        // Turn Coordinator - Load SVG path along which the slip/skid ball moves
        function _loadBallPath() {

            if (typeof(d3) != 'undefined') {

                // If running directly from the file, this will fail in Chrome due to security reasons
                try {
                    placeholder.each(function(){
                        var i = this;
                        d3.xml(settings.img_directory + "turn_ball_path.svg", "image/svg+xml", function(xml) {
                            $(i).find('div.instrument.turn div.turn_ball_path').append(xml.documentElement);
                        });
                    });

                // Inject SVG path via JS if the code above doesn't work
                } catch (err) {
                    console.log("Unable to load turn_ball_path.svg. Injecting a path instead.");
                    placeholder.each(function(){
                        d3.select($(this).find('div.instrument.turn div.turn_ball_path')[0]).append("svg")
                            .attr("width", 400)
                            .attr("height", 400)
                            .attr("class", "box")
                            .append("path")
                                .attr("id", "move_path")
                                // This line must be updated if the path SVG file is altered
                                .attr("d", "m 126.04736,251.79367 c 32.2868,5.88557 51.30081,7.6955 74.28947,7.69341 22.93061,0.002 41.52108,-1.7986 73.61092,-7.64849");
                    });
                }

            } else console.log("Unable to find d3js. Will not animate slip ball.");

        }

        // Turn Coordinator - Set turn direction
        function _setTurn(turn) {
            placeholder.each(function(){
                $(this).find('div.instrument.turn div.turn_airplane')
                    .css('transform', 'rotate('+ turn +'deg)')
                    .css('transition', 'transform 0.2s linear');
            });
        }

        // Turn Coordinator - Set slip/skid factor
        function _setSlip(slip) {

            // Animate slip ball only if d3js is loaded
            if (typeof(d3) !== undefined) {
                placeholder.each(function(){
                    var path = $("#move_path")[0], pathLength;
                    if (path !== undefined) {
                        var scale = $(this).find('div.instrument.turn').width() / 400;
                        if (slip < 0) slip = 0;
                        else if (slip > 1) slip = 1;
                        var pos = path.getPointAtLength( path.getTotalLength() * slip );
                        $(this).find('div.instrument.turn div.turn_ball')
                                    .css('transform', 'translate(' + (pos.x - 200) * scale + 'px, ' + (pos.y - 260) * scale + 'px)')
                                    .css('transition', 'transform 0.5s linear');
                    }
                });
            }

        }

        // Heading - Set heading
        function _setHeading(heading){
            placeholder.each(function(){
                $(this).find('div.instrument.heading div.heading_yaw').css('transform', 'rotate(' + -heading + 'deg)');
            });    
        }

        // Heading - Set beacon one direction
        function _setBeaconOne(heading, visible){
            if (visible) placeholder.each(function(){
                $(this).find('div.instrument.heading div.heading_beacon_1').show().css('transform', 'rotate(' + heading + 'deg)');
            });    
            else placeholder.each(function(){
                $(this).find('div.instrument.heading div.heading_beacon_1').hide();
            });
        }        

        // Heading - Set beacon two direction
        function _setBeaconTwo(heading, visible){
            if (visible) placeholder.each(function(){
                $(this).find('div.instrument.heading div.heading_beacon_2').show().css('transform', 'rotate(' + heading + 'deg)');
            });    
            else placeholder.each(function(){
                $(this).find('div.instrument.heading div.heading_beacon_2').hide();
            });
        }

        // Variometer - Set vertical speed
        function _setVario(vario){

            var deg = Math.sign(vario) * Math.min(Math.abs(vario), 20) * 8.2;
            if (vario > 20 || vario < - 20) deg += vario % 2;

            placeholder.each(function(){
                $(this).find('div.instrument.vario div.vario_hand')
                    .css('transform', 'rotate(' + deg + 'deg)')
                    .css('transition', 'transform 1.0s linear');

            });    
        }

        // Set size of instrument
        function _resize(size){
            var sz = (size < 100) ? sz = 100 : sz = size;
            placeholder.each(function(){
                $(this).find('div.instrument').css({height : sz, width : sz});
            });
        }

        // Toggle background box for instrument
        function _toggleBox(toggle){
            placeholder.each(function(){
                $(this).find('.indicator_background').toggle(toggle);
            });
        }

        // Toggle dashboard screws for instrument
        function _toggleScrews(toggle){
            placeholder.each(function(){
                $(this).find('.indicator_background_screws').toggle(toggle);
            });
        }

        // Toggle inner indicator elements
        function _toggleIndicatorInner(toggle){
            placeholder.each(function(){
                $(this).find('.indicator_inner').toggle(toggle);
            });
        }

        // Creation of the instrument
        placeholder.each(function(){

            switch(type){

                case 'airspeed':
                    $(this).html('<div class="instrument airspeed"><div class="indicator_background"><img src="' + settings.img_directory + 'indicator_background_dashboard.svg" class="box" alt="" /></div><div class="indicator_background_screws"><img src="' + settings.img_directory + 'indicator_background_screws.svg" class="box" alt="" /></div><div class="indicator_inner"><div class="airspeed_trueairspeed"><img src="' + settings.img_directory + 'airspeed_trueairspeed.svg" class="box" alt="" /></div><div class="airspeed_markings"><img src="' + settings.img_directory + 'airspeed_markings.svg" class="box" alt="" /></div><div class="airspeed box"><img src="' + settings.img_directory + 'airspeed_hand.svg" class="box" alt="" /></div></div><div class="indicator_foreground"><img src="' + settings.img_directory + 'indicator_foreground.svg" class="box" alt="" /></div></div>');
                    _setAirSpeed(settings.airspeed);
                    _setTrueAirSpeed(settings.trueairspeed);
                break

                case 'attitude':
                    $(this).html('<div class="instrument attitude"><div class="indicator_background"><img src="' + settings.img_directory + 'indicator_background_dashboard.svg" class="box" alt="" /></div><div class="indicator_background_screws"><img src="' + settings.img_directory + 'indicator_background_screws.svg" class="box" alt="" /></div><div class="indicator_inner"><div class="attitude box"><img src="' + settings.img_directory + 'attitude_roll_1.svg" class="box" alt="" /><div class="attitude_pitch box"><img src="' + settings.img_directory + 'attitude_pitch.svg" class="box" alt="" /></div><img src="' + settings.img_directory + 'attitude_roll_2.svg" class="box" alt="" /></div><div class="attitude_foreground_1"><img src="' + settings.img_directory + 'attitude_foreground_1.svg" class="box" alt="" /></div><div class="attitude_ils"><img src="' + settings.img_directory + 'attitude_ils_markings.svg" class="box" alt="" /><div class="attitude_ils_localizer box"><img src="' + settings.img_directory + 'attitude_ils_localizer.svg" class="box" alt="" /></div><div class="attitude_ils_glideslope box"><img src="' + settings.img_directory + 'attitude_ils_glideslope.svg" class="box" alt="" /></div></div><div class="attitude_foreground_2"><img src="' + settings.img_directory + 'attitude_foreground_2.svg" class="box" alt="" /></div><div class="attitude_off_flag"><img src="' + settings.img_directory + 'attitude_off_flag.svg" class="box" alt="" /></div></div><div class="indicator_foreground"><img src="' + settings.img_directory + 'indicator_foreground.svg" class="box" alt="" /></div></div>');
                    _setRoll(settings.roll);
                    _setPitch(settings.pitch);
                    _setOffFlag(settings.off_flag);
                    _setILS(settings.ils);
                    _setILSLocalizer(settings.ils_localizer);
                    _setILSGlideslope(settings.ils_glideslope);
                break

                case 'altimeter':
                    $(this).html('<div class="instrument altimeter"><div class="indicator_background"><img src="' + settings.img_directory + 'indicator_background_dashboard.svg" class="box" alt="" /></div><div class="indicator_background_screws"><img src="' + settings.img_directory + 'indicator_background_screws.svg" class="box" alt="" /></div><div class="indicator_inner"><div class="altimeter_pressureinhg box"><img src="' + settings.img_directory + 'altimeter_pressure_inhg.svg" class="box" alt="" /></div><div class="altimeter_pressurembar box"><img src="' + settings.img_directory + 'altimeter_pressure_mbar.svg" class="box" alt="" /></div><div class="altimeter_background box"><img src="' + settings.img_directory + 'altimeter_background.svg" class="box" alt="" /></div><div class="altimeter_hand10000 box"><img src="' + settings.img_directory + 'altimeter_hand_10000ft.svg" class="box" alt="" /></div><div class="altimeter_foreground box"><img src="' + settings.img_directory + 'altimeter_foreground.svg" class="box" alt="" /></div><div class="altimeter_hand1000 box"><img src="' + settings.img_directory + 'altimeter_hand_1000ft.svg" class="box" alt="" /></div><div class="altimeter_hand100 box"><img src="' + settings.img_directory + 'altimeter_hand_100ft.svg" class="box" alt="" /></div></div><div class="indicator_foreground"><img src="' + settings.img_directory + 'indicator_foreground.svg" class="box" alt="" /></div></div>');
                    _setAltitude(settings.altitude);
                    _setPressure(settings.pressure);
                break;

                case 'turn_coordinator':
                    $(this).html('<div class="instrument turn"><div class="indicator_background"><img src="' + settings.img_directory + 'indicator_background_dashboard.svg" class="box" alt="" /></div><div class="indicator_background_screws"><img src="' + settings.img_directory + 'indicator_background_screws.svg" class="box" alt="" /></div><div class="indicator_inner"><div class="turn_markings_1 box"><img src="' + settings.img_directory + 'turn_markings_1.svg" class="box" alt="" /></div><div class="turn_ball_path box" hidden></div><div class="turn_ball box"><img src="' + settings.img_directory + 'turn_ball.svg" class="box" alt="" /></div><div class="turn_airplane box"><img src="' + settings.img_directory + 'turn_airplane.svg" class="box" alt="" /></div><div class="turn_markings_2 box"><img src="' + settings.img_directory + 'turn_markings_2.svg" class="box" alt="" /></div></div><div class="indicator_foreground"><img src="' + settings.img_directory + 'indicator_foreground.svg" class="box" alt="" /></div></div>');
                    _loadBallPath();
                    _setTurn(settings.turn);
                    _setSlip(settings.slip);
                break;

                case 'heading':-
                    $(this).html('<div class="instrument heading"><div class="indicator_background"><img src="' + settings.img_directory + 'indicator_background_dashboard.svg" class="box" alt="" /></div><div class="indicator_background_screws"><img src="' + settings.img_directory + 'indicator_background_screws.svg" class="box" alt="" /></div><div class="indicator_inner"><div class="heading_background box"><img src="' + settings.img_directory + 'heading_background.svg" class="box" alt="" /></div><div class="heading_yaw box"><img src="' + settings.img_directory + 'heading_yaw.svg" class="box" alt="" /></div><div class="heading_beacon_2 box"><img src="' + settings.img_directory + 'heading_beacon_2.svg" class="box" alt="" /></div><div class="heading_beacon_1 box"><img src="' + settings.img_directory + 'heading_beacon_1.svg" class="box" alt="" /></div><div class="heading_markings box"><img src="' + settings.img_directory + 'heading_markings.svg" class="box" alt="" /></div></div><div class="indicator_foreground"><img src="' + settings.img_directory + 'indicator_foreground.svg" class="box" alt="" /></div></div>');
                    _setHeading(settings.heading);
                    _setBeaconTwo(settings.beacontwo, settings.beacontwoshow);
                    _setBeaconOne(settings.beaconone, settings.beacononeshow);
                break;

                case 'variometer':
                    $(this).html('<div class="instrument vario"><div class="indicator_background"><img src="' + settings.img_directory + 'indicator_background_dashboard.svg" class="box" alt="" /></div><div class="indicator_background_screws"><img src="' + settings.img_directory + 'indicator_background_screws.svg" class="box" alt="" /></div><div class="indicator_inner"><div class="vario_markings"><img src="' + settings.img_directory + 'vario_markings.svg" class="box" alt="" /></div><div class="vario_hand box"><img src="' + settings.img_directory + 'vario_hand.svg" class="box" alt="" /></div></div><div class="indicator_foreground"><img src="' + settings.img_directory + 'indicator_foreground.svg" class="box" alt="" /></div></div>');
                    _setVario(settings.vario);
                break;

                default:
                    built = false;
                    console.log("No instrument built.");

            }

            _resize(settings.size);
            _toggleBox(settings.showBox);
            _toggleScrews(settings.showScrews);
            _toggleIndicatorInner(settings.showIndicatorInner);

        });

        // Public methods
        this.setAirSpeed = function(speed){_setAirSpeed(speed);}
        this.setTrueAirSpeed = function(speed){_setTrueAirSpeed(speed);}
        this.setRoll = function(roll){_setRoll(roll);}
        this.setPitch = function(pitch){_setPitch(pitch);}
        this.setOffFlag = function(visible){_setOffFlag(visible);}
        this.setILS = function(visible){_setILS(visible);}
        this.setILSLocalizer = function(angle){_setILSLocalizer(angle);}
        this.setILSGlideslope = function(angle){_setILSGlideslope(angle);}
        this.setAltitude = function(altitude){_setAltitude(altitude);}
        this.setPressure = function(pressure, milibar){_setPressure(pressure, milibar);}
        this.setTurn = function(turn){_setTurn(turn);}
        this.setSlip = function(slip){_setSlip(slip);}
        this.setHeading = function(heading){_setHeading(heading);}
        this.setBeaconOne = function(heading, visible){_setBeaconOne(heading, visible);}
        this.setBeaconTwo = function(heading, visible){_setBeaconTwo(heading, visible);}
        this.setVario = function(vario){_setVario(vario);}
        this.resize = function(size){_resize(size);}
        this.toggleBox = function(toggle){_toggleBox(toggle);}
        this.toggleScrews = function(toggle){_toggleScrews(toggle);}
        this.toggleIndicatorInner = function(toggle){_toggleIndicatorInner(toggle);}

        return built;
    };

    // Extension to jQuery
    $.flightIndicator = function(placeholder, type, options){
        var flightIndicator = new FlightIndicator($(placeholder), type, options);
        return flightIndicator;
    };

    $.fn.flightIndicator = function(data, type, options){
        return this.each(function(){
            $.flightIndicator(this, type, options);
        });
    };

}( jQuery ));
