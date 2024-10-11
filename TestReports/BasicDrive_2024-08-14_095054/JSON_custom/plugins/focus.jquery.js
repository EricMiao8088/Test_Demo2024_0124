// Utility
if ( typeof Object.create !== 'function' ) {
	Object.create = function( obj ) {
		function F() {};
		F.prototype = obj;
		return new F();
	};
}

;(function($,window,document,undefined) {
	var FocusObject = {
		init: function(options,elem) {
			var self=this;

			self.$elem=$(elem);

			self.parent = self.$elem.parent();

			self.options=$.extend({},$.fn.Focus.defaults,options);

			if(self.parent.data('hasFocus') == self.$elem.prop('id')) {
				self.$elem.append('<aside class="highlightLine">&nbsp;</aside>');
			}

			self.$elem.on('click',function(event) {
				if(event.type == 'click') {
					if(self.parent.data('hasFocus') === false) { // kein focus vorhanden
						self.$elem.append('<aside class="highlightLine">&nbsp;</aside>');
						self.parent.data('hasFocus',self.$elem.prop('id'));
					} else if (self.parent.data('hasFocus') == self.$elem.prop('id')) { // focus auf sich selbst
						// nichts zu tun
					} else { // focus woanders
						$('#'+self.parent.data('hasFocus')).find('aside').remove();
						self.$elem.append('<aside class="highlightLine">&nbsp;</aside>');
						self.parent.data('hasFocus',self.$elem.prop('id'));
					}
				}
			});
		}
	};

	$.fn.Focus=function(options) {
		return this.each(function() {
			if ( $(this).parent().data('hasFocus') == 'undefined' ) {
				$(this).parent().data('hasFocus',false);
			}

			var focusInstance = Object.create(FocusObject);
			focusInstance.init(options,this);
			$.data(this,'Focus',focusInstance);
		});
	};

	$.fn.Focus.defaults = {
		// default parameter
	};
})(jQuery,window,document);