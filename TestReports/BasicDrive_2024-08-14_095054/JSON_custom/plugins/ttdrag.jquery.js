// Utility
if ( typeof Object.create !== 'function' ) {
	Object.create = function( obj ) {
		function F() {};
		F.prototype = obj;
		return new F();
	};
}

;(function($, window, document, undefined) {
	var Drag = {
		init: function( options, elem ) {
			var self = this;

			self.elem = elem;
			self.$elem = $( elem );

			self.options = $.extend( {}, $.fn.ttDrag.options, options );

			var dragbar = self.$elem.find(self.options.dragHandle).length == 1 ? self.$elem.find(self.options.dragHandle) : self.$elem,
				cx, cy, sx, sy;

			dragbar.on('mousedown mouseup mousemove mouseover',function(event) {
				if(event.type =='mousedown') {
					$('.ttWindow').css('z-index',3000);
					self.$elem.css('z-index',3010);
					self.$elem.find('.goto').css('display','inline');
					self.$elem.find('span').remove();
					sx = event.pageX;
					cx = parseInt(self.$elem.css('left'), 10);
					sy = event.pageY;
					cy = parseInt(self.$elem.css('top'), 10);
					$(document).on('mousemove', function(event2) {
						self.$elem.css('left', (cx + event2.pageX - sx) + 'px').css('top', (cy + event2.pageY - sy) + 'px');
					});
				} else if(event.type == 'mouseup') {
					$(document).off('mousemove');
				} else if(event.type == 'mouseover') {
					dragbar.css('cursor','move');
				}
			});
		}
	};

	$.fn.ttDrag = function(options) {
		return this.each(function() {
			var drag = Object.create(Drag);
			drag.init(options, this);
			$.data(this, 'ttDrag', drag);
		});
	};

	$.fn.ttDrag.options = { // Default Parameter
		dragHandle: '.ttHead'
	};
})(jQuery, window, document);