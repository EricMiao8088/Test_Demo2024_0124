    dispStyle = "table-row";
    if (navigator.appName.indexOf("Microsoft") != -1) dispStyle = "block"; 

    function getNextSibling(o)
    {
        var ns = o;
        do ns = ns.nextSibling;
        while (ns && ns.nodeType != 1);
        return ns;
    }
    function getFirstChild(o)
    {
        var fs = o.firstChild;
        while (fs && fs.nodeType != 1) fs = fs.nextSibling;
        return fs;
    }
    
    function expand(id) 
    {
        var item = document.getElementById('item_' + id);
        var col = getFirstChild(getFirstChild(item));
        if(item != null) {
            var entity = getNextSibling(item);
            while (entity != null) {
                if (entity.style.display != "none") { 
                    entity.style.display = "none"; 
                    col.innerHTML = "+";
                } else { 
                    entity.style.display = dispStyle; 
                    col.innerHTML = "&minus;";
                }
                entity = getNextSibling(entity);
            }
        }
    }
  

    function collapseAll() 
    {
        var ele = document.getElementsByTagName("tr");
        for (var i = 0; i < ele.length; i++) {
            id = ele[i].id;
            if (id.indexOf("item") == -1) continue;
            var item = ele[i];
            var col = getFirstChild(getFirstChild(item));
            var entity = getNextSibling(item);
            while (entity != null) {
                entity.style.display = "none"; 
                col.innerHTML = "+";                
                entity = getNextSibling(entity);
            }
        }
    }
  
    function expandAll() 
    {
        var ele = document.getElementsByTagName("tr");
        for (var i = 0; i < ele.length; i++) {
            id = ele[i].id;
            if (id.indexOf("item") == -1) continue;
            var item = ele[i];
            var col = getFirstChild(getFirstChild(item));
            var entity = getNextSibling(item);
            while (entity != null) {
                entity.style.display = dispStyle; 
                col.innerHTML = "&minus;";                
                entity = getNextSibling(entity);
            }
        }
    }
    
    function toggleNavi(e) 
    {
        //don't propagate events
        if (!e) var e = window.event;
        e.cancelBubble = true;
        if (e.stopPropagation) e.stopPropagation();
        
        var subContent = getNextSibling(getFirstChild(this));
        if (subContent.style.display != "none") { 
            subContent.style.display = "none"; 
            this.className = "close";
        } else { 
            subContent.style.display = "block"; 
            this.className = "open";
        }        
    }
    
    function injectNavi() {
        var x = document.getElementsByTagName('LI');
        for (var i=0;i<x.length;i++) {
            if (x[i].className != "") {
                x[i].ondblclick = toggleNavi;
            }        
        }
    }