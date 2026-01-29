
const multipleItemCarousel = document.querySelector("#testimonialCarousel");

if (window.matchMedia("(min-width:576px)").matches) {
  const carousel = new bootstrap.Carousel(multipleItemCarousel, {
    interval: false
  });

  const carouselInner = document.querySelector(".carousel-inner");
  const carouselItems = document.querySelectorAll(".carousel-item");
  const carouselWidth = carouselInner.scrollWidth;
  const cardWidth = carouselItems[0].offsetWidth;

  let scrollPosition = 0;
  let indexScrol=0;

  document.querySelector(".carousel-control-next").addEventListener("click", function () {
    if (scrollPosition <= carouselWidth - cardWidth * 3) {
      //carouselItems[indexScrol].style.background = 'white';
      //carouselItems[++indexScrol].style.background = 'blue';
      //... ("next"  + "  : " + indexScrol);
      //... console.log("scrollPosition=" + scrollPosition);
      scrollPosition += cardWidth;
      //... console.log("New scrollPosition=" + scrollPosition);
      carouselInner.scrollTo({
        left: scrollPosition,
        behavior: "smooth"
      });
      
    } else {
      //carouselItems[indexScrol].style.background = 'white'; 
      indexScrol=0; 
      //... console.log("scrollPosition=" + scrollPosition);
        
        scrollPosition = 0 ;
        //... console.log("NewscrollPosition=" + scrollPosition);
        carouselInner.scrollTo({
            left: scrollPosition,
            behavior: "smooth"
          });
    }
  });

  document.querySelector(".carousel-control-prev").addEventListener("click", function () {
    if (scrollPosition > 0) {
      scrollPosition -= cardWidth;
      carouselInner.scrollTo({
        left: scrollPosition,
        behavior: "smooth"
      });
    } else {
        scrollPosition = carouselWidth - cardWidth * 3
        carouselInner.scrollTo({
            left: scrollPosition,
            behavior: "smooth"
          });
    }
  });
} else {
  multipleItemCarousel.classList.add("slide");
}

setInterval(() => {
    document.querySelector(".carousel-control-next").click();
}, 5000); 





function reveal() {
  const squares = document.querySelectorAll('.square');

  squares.forEach(square => {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          square.classList.add('active');
          return;
        }

        square.classList.remove('active');
      });
    });

    observer.observe(square);
  });
}

// Call the function to initialize the scroll animations
reveal();

const elements = document.querySelectorAll(".animate-on-scroll");
const elements_zoom_in = document.querySelectorAll(".animate-on-scroll-zoom-in");
const elements_zoom_out = document.querySelectorAll(".animate-on-scroll-zoom-out");
const elements_fade_up = document.querySelectorAll(".animate-on-scroll-fade-up");
const elements_fade_up1 = document.querySelectorAll(".animate-on-scroll-fade-up1");
const elements_fade_up2 = document.querySelectorAll(".animate-on-scroll-fade-up2");
const elements_fade_up3 = document.querySelectorAll(".animate-on-scroll-fade-up3");
const elements_fade_up4 = document.querySelectorAll(".animate-on-scroll-fade-up4");

function handleScroll() {
  elements.forEach(element => {
    const rect = element.getBoundingClientRect();
    const viewHeight = window.innerHeight;

    if (rect.top < viewHeight && rect.bottom > 0) {
      setTimeout(() => {
        element.classList.add("in-view");  
      }, 400);
    } else {
      element.classList.remove("in-view");
    }
  });

  elements_zoom_in.forEach(element => {
    const rect = element.getBoundingClientRect();
    const viewHeight = window.innerHeight;

    if (rect.top < viewHeight && rect.bottom > 0) {
      setTimeout(() => {
        element.classList.add("in-view");  
      }, 400);
    } else {
      element.classList.remove("in-view");
    }
  });

  elements_zoom_out.forEach(element => {
    const rect = element.getBoundingClientRect();
    const viewHeight = window.innerHeight;

    if (rect.top < viewHeight && rect.bottom > 0) {
      setTimeout(() => {
        element.classList.add("in-view");  
      }, 400);
    } else {
      element.classList.remove("in-view");
    }
  });

  elements_fade_up.forEach(element => {
    const rect = element.getBoundingClientRect();
    const viewHeight = window.innerHeight;

    if (rect.top < viewHeight && rect.bottom > 0) {
      setTimeout(() => {
        element.classList.add("in-view");  
      }, 100);
    } else {
      element.classList.remove("in-view");
    }
  });

  elements_fade_up1.forEach(element => {
    const rect = element.getBoundingClientRect();
    const viewHeight = window.innerHeight;

    if (rect.top < viewHeight && rect.bottom > 0) {
      setTimeout(() => {
        element.classList.add("in-view");  
      }, 400);
    } else {
      element.classList.remove("in-view");
    }
  });

  elements_fade_up2.forEach(element => {
    const rect = element.getBoundingClientRect();
    const viewHeight = window.innerHeight;

    if (rect.top < viewHeight && rect.bottom > 0) {
      setTimeout(() => {
        element.classList.add("in-view");  
      }, 400);
    } else {
      element.classList.remove("in-view");
    }
  });

  elements_fade_up3.forEach(element => {
    const rect = element.getBoundingClientRect();
    const viewHeight = window.innerHeight;

    if (rect.top < viewHeight && rect.bottom > 0) {
      setTimeout(() => {
        element.classList.add("in-view");  
      }, 400);
    } else {
      element.classList.remove("in-view");
    }
  });

  elements_fade_up4.forEach(element => {
    const rect = element.getBoundingClientRect();
    const viewHeight = window.innerHeight;

    if (rect.top < viewHeight && rect.bottom > 0) {
      setTimeout(() => {
        element.classList.add("in-view");  
      }, 400);
    } else {
      element.classList.remove("in-view");
    }
  });

}

window.addEventListener("scroll", handleScroll);
window.addEventListener("load", handleScroll);


const divs = document.querySelectorAll('.presantation-image');
        let currentIndex = 0;

        function showNextDiv() {
            divs[currentIndex].style.display = 'none';
            divs[currentIndex].style.transform ='scale(1, 1)';
            divs[currentIndex].style.opacity = '0%';
            
            currentIndex = (currentIndex + 1) % divs.length;
            
            divs[currentIndex].style.display = 'block';
            
            setTimeout(() => {
              divs[currentIndex].style.opacity = '100%';
            }, 50);

            setTimeout(() => {
              divs[currentIndex].style.transform ='scale(1.07, 1.07)';
              divs[currentIndex].style.opacity = '100%';
            }, 100);
           
            
            //divs[currentIndex].add("in-view")
            //... console.log(currentIndex);
        }
        showNextDiv();
       setInterval(showNextDiv, 3000); // Switch every 1500 ms



       // Instantiate the Bootstrap carousel
var carousel = document.querySelector('.multi-item-carousel');
if (carousel) {
  var carouselInstance = new bootstrap.Carousel(carousel, {
    interval: false
  });
}

// For every slide in carousel, copy the next slide's item in the slide.
// Do the same for the next, next item.
var items = document.querySelectorAll('.multi-item-carousel .item');
items.forEach(function(item) {
  var next = item.nextElementSibling;
  if (!next) {
    next = item.parentElement.firstElementChild;
  }
  var clone = next.firstElementChild.cloneNode(true);
  item.appendChild(clone);

  if (next.nextElementSibling) {
    var nextNext = next.nextElementSibling.firstElementChild.cloneNode(true);
    item.appendChild(nextNext);
  } else {
    var firstChild = item.parentElement.firstElementChild.firstElementChild.cloneNode(true);
    item.appendChild(firstChild);
  }
});

