var handle_click = function () {
	var cid = $(this).closest('div').attr('id');
	return fetch("/customers/" + cid + "/charge", {
		method: "post",
    headers: {
      "Content-Type": "application/json"
		}
	}).then(function(response) {
		return response.json();
	})
		.then(function(response) {
		console.log(response);
		$("#result")
			.append($("<pre></pre>")
				.text(JSON.stringify(response, null, '\t'))
			)
			.show(); /* TODO Stringify that JSON*/
	});

}
var getCustomers = function() {
  return fetch("/customers", {
    method: "get",
    headers: {
      "Content-Type": "application/json"
    }
  })
    .then(function(response) {
      return response.json();
    })
    .then(function(response) {
			var container = $('#customers');
			$.each(response, function(c, b)
			{
				var info = [b.name, b.email, b.address, b.number, b.type, b.exp].join(' | ');
				console.log(b);
				container.append(
					$('<div></div>')
					.attr('id', c)
					.text(info)
					.append(
						$('<button></button>')
							.html("Charge Customer")
							.click(handle_click)
					)
				);
			})
    });
};

getCustomers();
