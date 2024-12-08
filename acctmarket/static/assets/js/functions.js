// -------------------------------------- Document Ready - Review Form Submission
/**
 * Handles the submission of the review form via AJAX.
 * Prevents default form submission, sends data to the server,
 * and updates the UI dynamically based on the server response.
 */
$(document).ready(function () {
    $("#reviewform").submit(function (e) {
        e.preventDefault(); // Prevent default form submission

        $.ajax({
            data: $(this).serialize(), // Serialize form data
            method: $(this).attr("method"), // Get the HTTP method from the form
            url: $(this).attr("action"), // Get the form's action URL
            dataType: "json", // Expect JSON response
            success: function (response) {
                console.log("Comment saved", response);

                if (response.bool === true) {
                    $("#review-comment").html("<h2>Review Added successfully</h2>");
                    $(".hide-comment-form").hide(); // Hide the form after success

                    let context = response.context;
                    let created_at = new Date().toLocaleDateString('en-GB', {
                        day: '2-digit',
                        month: 'short',
                        year: 'numeric'
                    });

                    // Generate a unique ID for the new comment
                    let commentId = `comments-${context.id}`;

                    // Check if the comment already exists to avoid duplicates
                    if ($(`#${commentId}`).length === 0) {
                        let _html = `
                          <li class="comment-list" id="${commentId}">
                            <div class="comment-avatar text-center">
                              <img src="${staticUrl}" alt="" />
                              <div class="product-rating mt-10">
                                ${generateStarRating(context.rating)}
                              </div>
                            </div>
                            <div class="comment-desc">
                              <span>${created_at}</span>
                              <h4>${context.user.name}</h4>
                              <p>${context.review}</p>
                            </div>
                          </li>`;
                        $(".comments-container").prepend(_html); // Add the comment to the list
                    } else {
                        console.log("Comment already exists.");
                    }
                } else {
                    console.error("Failed to save comment:", response.errors);
                }
            },
            error: function (xhr, status, error) {
                console.error("AJAX error:", status, error);
            }
        });
    });

    /**
     * Helper function to generate star rating HTML.
     * @param {number} rating - The rating value.
     * @returns {string} HTML string with star icons.
     */
    function generateStarRating(rating) {
        let fullStars = Math.floor(rating);
        let emptyStars = 5 - fullStars;

        let starHtml = '';

        for (let i = 0; i < fullStars; i++) {
            starHtml += '<i class="fa fa-star"></i>'; // Full star
        }

        for (let i = 0; i < emptyStars; i++) {
            starHtml += '<i class="fa fa-star-o"></i>'; // Empty star
        }

        return starHtml;
    }
});

// -------------------------------------- Filter Products
/**
 * Handles filtering of products based on selected criteria (e.g., price, attributes).
 */
$(document).ready(function () {
    $(".filter-checkbox, #price-filter-btn").on("click", function () {
        console.log("Checkbox or button clicked");

        let filter_object = {};

        let min_price = $("#max_price").attr("min");
        let max_price = $("#max_price").val();

        if (min_price) filter_object.min_price = min_price;
        if (max_price) filter_object.max_price = max_price;

        $(".filter-checkbox").each(function () {
            let filter_key = $(this).data("filter");
            filter_object[filter_key] = Array.from(
                document.querySelectorAll(`input[data-filter="${filter_key}"]:checked`)
            ).map(element => element.value);
        });

        console.log("Filter object is", filter_object);

        $.ajax({
            url: "/filter-product",
            data: filter_object,
            dataType: "json",
            beforeSend: function () {
                console.log("Before send");
            },
            success: function (response) {
                console.log("Success");
                $("#filtered-product").html(response.data);
            },
            error: function (xhr, status, error) {
                console.log("Error:", error);
            }
        });
    });

    // Validate price input when it loses focus
    $("#max_price").on("blur", function () {
        let min_price = $(this).attr("min");
        let max_price = $(this).attr("max");
        let current_price = $(this).val();

        if (current_price < parseInt(min_price) || current_price > parseInt(max_price)) {
            alert(`Price must be between $${min_price} and $${max_price}`);
            $(this).val(min_price).focus();
            return false;
        }
    });
});

// -------------------------------------- Add to Cart
/**
 * Adds a product to the shopping cart via AJAX and updates the UI.
 */
$(".add-to-cart-btn").on("click", function () {
    let this_val = $(this);
    let index = this_val.attr("data-index");

    let quantity = $(".product-quantity-" + index).val();
    let product_id = $(".product-pid-" + index).val();
    let product_title = $(".product-title-" + index).val();
    let product_price = $("#product-price-" + index).text();
    let product_image = $(".product-image-" + index).val();

    $.ajax({
        url: "/ecommerce/add-to-cart",
        data: {
            id: product_id,
            qty: quantity,
            image: product_image,
            title: product_title,
            price: product_price
        },
        dataType: "json",
        beforeSend: function () {
            this_val.html("Adding...");
        },
        success: function (response) {
            this_val.html("Added 👍");
            $(".cart-item-count").text(response.totalcartitems);
        }
    });
});

// -------------------------------------- Manage Cart Items
/**
 * Handles updating and deleting items in the shopping cart dynamically.
 */
$(document).ready(function () {
    function attachHandlers() {
        $(".delete-product").off("click").on("click", function (e) {
            e.preventDefault();
            let product_id = $(this).data("product");
            let this_value = $(this);

            $.ajax({
                url: "/ecommerce/delete-from-cart",
                data: { id: product_id },
                dataType: "json",
                beforeSend: function () {
                    this_value.hide();
                },
                success: function (response) {
                    $(".cart-item-count").text(response.totalcartitems);
                    $("#cart-list").html(response.data);
                    attachHandlers();
                },
                error: function () {
                    this_value.show();
                }
            });
        });

        $(".update-product").off("click").on("click", function (e) {
            e.preventDefault();
            let product_id = $(this).data("product");
            let new_quantity = $(this).closest("tr").find("input[type='text']").val();

            $.ajax({
                url: "/ecommerce/update-to-cart",
                data: { id: product_id, quantity: new_quantity },
                dataType: "json",
                beforeSend: function () {
                    $(this).hide();
                },
                success: function (response) {
                    $(".cart-item-count").text(response.totalcartitems);
                    $("#cart-list").html(response.data);
                    attachHandlers();
                }
            });
        });
    }

    attachHandlers();
});

// -------------------------------------- Add to Wishlist
/**
 * Adds a product to the user's wishlist via AJAX and updates the wishlist count.
 */
$(".add-to-wishlist").on("click", function () {
    let this_val = $(this);
    let product_id = $(this).attr("data-product-item");

    $.ajax({
        url: "/ecommerce/add-to-wishlist",
        data: { id: product_id },
        dataType: "json",
        beforeSend: function () {
            this_val.html("❤️");
        },
        success: function (response) {
            if (response.bool === true) {
                this_val.html("❤️");
                $(".wishlist-item-count").text(response.totalwishlistitems);
            }
        }
    });
});

// -------------------------------------- Countdown Timer
/**
 * Initializes countdown timers for elements with a `data-countdown-end` attribute.
 * @param {Date} endTime - The countdown end time.
 * @param {HTMLElement} element - The DOM element to update.
 */
document.addEventListener("DOMContentLoaded", function () {
    var countdownElements = document.querySelectorAll("[data-countdown-end]");

    countdownElements.forEach(function (element) {
        var endTime = new Date(element.getAttribute("data-countdown-end")).getTime();
        countdownTimer(endTime, element);
    });
});

function countdownTimer(endTime, element) {
    var x = setInterval(function () {
        var now = new Date().getTime();
        var distance = endTime - now;

        var days = Math.floor(distance / (1000 * 60 * 60 * 24));
        var hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        var minutes = Math.floor((distance % (1000 * 60)) / (1000 * 60));
        var seconds = Math.floor((distance % 1000) / 1000);

        element.innerHTML = `${days}d ${hours}h ${minutes}m ${seconds}s`;

        if (distance < 0) {
            clearInterval(x);
            element.innerHTML = "EXPIRED";
        }
    }, 1000);
}






document.addEventListener("DOMContentLoaded", function () {
    const slider = document.getElementById("range");
    const maxPriceInput = document.getElementById("max_price");

    // Sync input field with slider
    slider.addEventListener("input", function () {
        maxPriceInput.value = this.value;
    });

    // Optional: Ensure the slider works with touch events
    slider.addEventListener("touchmove", function (e) {
        const touch = e.touches[0];
        const boundingBox = slider.getBoundingClientRect();
        const sliderWidth = boundingBox.width;
        const sliderLeft = boundingBox.left;
        const position = touch.clientX - sliderLeft;
        const value = (position / sliderWidth) * (slider.max - slider.min) + parseFloat(slider.min);
        slider.value = Math.min(Math.max(value, slider.min), slider.max); // Clamp value
        maxPriceInput.value = slider.value;
    });
});
