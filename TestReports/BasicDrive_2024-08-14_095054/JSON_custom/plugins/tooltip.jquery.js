// Utility
if ( typeof Object.create !== 'function' ) {
	Object.create = function( obj ) {
		function F() {};
		F.prototype = obj;
		return new F();
	};
}

;(function($,window,document,undefined) {
	$.fn.lightbox = function(options) {	
		var $loading=$('#loading'),
			$lightbox=$('#lightbox'),
			$imgbox=$('#imgbox'),
			$prevImg=$('#prevImg'),
			$nextImg=$('#nextImg'),
			$hiddenlayer=$('#hiddenlayer'),
			toggleButtons=function(pos, max) {
				if ( pos > 0 ) {
					$prevImg.show();
				} else {
					$prevImg.hide();
				}
				if ( pos < max ) {
					$nextImg.show();
				} else {
					$nextImg.hide();
				}
			};
		return this.each(function() {
			var $self = $(this);
			$self.find('.smallPicture').on({
				mouseover: function() {
					$('.newTab', $(this)).show();
				},
				mouseout: function() {
					$('.newTab', $(this)).hide();
				}
			});

			// open lightbox on click
			var $previewImages = $self.find('.previewImage').click(function() {
				var $thisImg=$(this),
					pos=$previewImages.index( $thisImg ); // store position of current image in previewImages array

				toggleButtons(pos, $previewImages.length-1);

				$loading.hide();
				$lightbox.show().find('.navImg').on('click', function() { // compute prev/next navigation
					var $this = $(this);
					if( $this.prop('id') == 'prevImg' ) {
						// look for pevious img
						$imgbox.html('<img src="'+$($previewImages[pos-1]).attr('src')+'">');
						pos-=1;
					} else if( $this.prop('id' ) == 'nextImg') {
						// look for next img
						$imgbox.html('<img src="'+$($previewImages[pos+1]).attr('src')+'">');
						pos+=1;
					}
					toggleButtons(pos, $previewImages.length-1);
				});
				$imgbox.html('<img src="'+$(this).attr('src')+'">');
				$hiddenlayer.show();
			});
		});
	};

	var $window = $(window),
		$document = $(document),
		TooltipObject = {
		init: function(options,elem) {
			var self=this,
				tt_state=null,
				tt_timeout=null,
				$tt_handle=null;

			self.$elem=$(elem);
			self.elem=elem

			self.options=$.extend({},$.fn.Tooltip.defaults,options);

			self.$elem.on('mouseenter mouseleave dblclick click',function(event) {
				var id=self.options.id,
					tt_id='tt_'+id;

				if(event.type=='mouseenter') {
					if (reportConfig.enableTooltip) {
						if (tt_state==null) {
							tt_timeout=window.setTimeout(function() {
								if(window.globalVars.blockTimeout==self.options.blockTimeout || self.options.blockTimeout=='abc123') {
									$('.ttWindow',self.options.target).css('z-index',3000);
									var elemPos = $(self.$elem.children()[self.options.indentPos]).offset();
									$tt_handle=$('<div class="ttWindow" id="'+tt_id+'"><div class="ttHead"></div><div class="ttBody"></div></div>')
										.css({
											'left': -3000,
											'z-index': 3010
										})
										.appendTo(self.options.target)
										.ttDrag();

									$tt_handle.head=$('.ttHead',$tt_handle).append('<div class="ttTitle">'+self.options.title+'</div><a class="close">&nbsp;X&nbsp;</a>');
									$tt_handle.body=$('.ttBody',$tt_handle).html(self.options.body);
									
									// Tooltip ist links ausserhalb des sichtbaren Bildbereichs positioniert, Dimensionen ermitteln und im Tooltip speichern:
									self.nativeDims = {'height': $tt_handle.body.height(), 'width': $tt_handle.body.width()};
									$tt_handle.data('nativeDims',self.nativeDims);
									
									var win_height=$window.height(),
										win_width=$window.width();

									// Dimensionen der Elemente im TT Body fixieren
									if(self.nativeDims.width < 230) {
										$('.tableContainer',$tt_handle.body).width(230);
										self.nativeDims.width = 230
									} else {
										$('.tableContainer',$tt_handle.body).width(self.nativeDims.width);
									}

									// Tooltip an die vorgesehene Position ruecken:
									$tt_handle.css('left',elemPos.left);

									// anhand der Hoehe des Tooltips pruefen, ob der TT noch drunter passt und entsprechend positionieren
									var tt_height=$tt_handle.height(),
										space_above=win_height-elemPos.top,
										space_below=win_height-elemPos.top+self.options.lineHeight;

									if(tt_height+25 > space_below) {
										if(tt_height+25 < space_above) {
											$tt_handle.css('top',elemPos.top-tt_height-1);
										} else {
											$tt_handle.css('top',elemPos.top+self.options.lineHeight+1);
										}
									} else {
										$tt_handle.css('top',elemPos.top+self.options.lineHeight+1);
									}

									tt_state='open';
								}
							}, self.options.delay);
						}
					}
				} else if(event.type=='mouseleave') {
					window.clearTimeout(tt_timeout);
					if(tt_state=='open') {
						$tt_handle.remove();
						tt_state=null;
					}
				} else if(event.type=='click') {
					if(tt_state=='open') {
						tt_state='keep';
						$('.ttWindow',self.options.target).css('z-index',3000);
						$tt_handle
							.addClass('keep')
							.css('z-index',3010)
							.on('click',function() { // Focus triggern
								$('#'+self.$elem.attr('id')).trigger('click');
							});
						$('.ttTitle span', $tt_handle.head).text(self.options.titleDblClick);
						$('.close', $tt_handle.head)
							.css('visibility','visible')
							.on('click',function(event) { // Tooltip schließen
								event.preventDefault();
								$tt_handle.remove();
								tt_state=null;
							});

						var winWidth = $window.width(),
							winHeight = $window.height();
						if(winWidth < self.nativeDims.width) {
							$tt_handle.body.width(winWidth - parseInt( $tt_handle.css('left'), 10) );
						}
						if(winHeight < self.nativeDims.height) {
							var newDblClickHeight = winHeight - 50;
							$tt_handle.body.height(newDblClickHeight);
						}

						$tt_handle.body.on('click',function() {
							$('.ttWindow',self.options.target).css('z-index', 3000);
							$tt_handle.css('z-index',3010);
						}).lightbox();

						// manuell Skalieren
						if(self.options.resizable) {
							var $resizeHandle = $('<div class="resizeHandle"></div>').appendTo($tt_handle.body);
							$resizeHandle.on('mousedown mouseup dblclick',function(mouseclick_event) {
								mouseclick_event.preventDefault();
								if(mouseclick_event.type=='mousedown') {
									// initiale Mausposition beim mousedown:
									var mousex = mouseclick_event.pageX,
										mousey = mouseclick_event.pageY;
									
									$document.on('mousemove',function(move_event) {
										var mousexdelta = mousex - move_event.pageX,
											mouseydelta = mousey - move_event.pageY
											newWidth=$tt_handle.body.width()-mousexdelta,
											newHeight=$tt_handle.body.height()-mouseydelta;
										
										if(newWidth > 230 && newWidth <= self.nativeDims.width+10) {
											$tt_handle.body.width(newWidth);
											mousex = move_event.pageX;
										}
										if(newHeight > 25 && newHeight <= self.nativeDims.height+10) {
											$tt_handle.body.height(newHeight);
											mousey = move_event.pageY;
										}

										if (newHeight > self.nativeDims.height+10 && newWidth > self.nativeDims.width+10) {
											$resizeHandle.trigger('mouseup');
										}
									});
								} else if(mouseclick_event.type=='dblclick') {
									$tt_handle.body.width(self.nativeDims.width);
									$tt_handle.body.height(self.nativeDims.height);
								} else if(mouseclick_event.type=='mouseup') {
									$document.off('mousemove');
								}
							});
						}

						// Sprung zur id des Tooltips
						if(typeof self.options.gotoCallback==='function' ) {
							$('.goto', $tt_handle.head).on('click',function(event) {
								event.preventDefault();
								if(typeof self.options.staticIncrementor == 'number') {
									self.options.gotoCallback.call(self.elem,self.options.staticIncrementor)
								} else {
									self.options.gotoCallback.call(this,id);
								}
							});
						}
					}

					// enlarge small picture preview: fancy gallery and new tab handler
					if(reportConfig.enableInfoFrame===true && self.options.infoFrame!=null) {
						self.options.infoFrame.html(self.options.body).lightbox();
					}

				}/* else if(event.type=='click') {
					if(reportConfig.enableInfoFrame===true && self.options.infoFrame!=null) {
						self.options.infoFrame.html(self.options.body);
					}
				}*/
			}).css('cursor','help');
		}
	};

	$.fn.Tooltip=function(options) {
		return this.each(function() {
			var tto=Object.create(TooltipObject);
			tto.init(options,this);
			$.data(this,'Tooltip',tto);
		});
	};

	$.fn.Tooltip.defaults = { // Default Parameter
		id: 'id123',
		title: '<a href="#" style="text-decoration: none;">&nbsp;</a><span>Die &Uuml;berschrift ist hier.</span>',
		titleDblClick: 'Tooltip kann jetzt verschoben werden',
		body: 'Hier sollte der Inhalt erscheinen.',
		target: document.body,
		indentPos: 2,
		blockTimeout: 'abc123',
		delay: 200,
		lineHeight: 25,
		gotoCallback: function() {},
		resizable: true,
		infoFrame: null
	};
})(jQuery,window,document);