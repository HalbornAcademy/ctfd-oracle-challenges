CTFd._internal.challenge.data = undefined

CTFd._internal.challenge.renderer = CTFd.lib.markdown();

CTFd._internal.challenge.preRender = function () { }

CTFd._internal.challenge.render = function (markdown) {
    return CTFd._internal.challenge.renderer.render(markdown)
}


CTFd._internal.challenge.postRender = function () { }


CTFd._internal.challenge.submit = function (preview) {
    var challenge_id = parseInt(CTFd.lib.$('#challenge-id').val())

    var body = {
        'challenge_id': challenge_id
    }
    var params = {}
    if (preview) {
        params['preview'] = true
    }

    return CTFd.api.post_challenge_attempt(params, body).then(function (response) {
        if (response.status === 429) {
            // User was ratelimited but process response
            return response
        }
        if (response.status === 403) {
            // User is not logged in or CTF is paused.
            return response
        }
        return response
    })
};

getChallenge = function() {
    var challenge_id = CTFd.lib.$('#challenge-id-oracle').val()
    var url = "/plugins/oracle_challenges/" + challenge_id;

    var params = {
        'force_new': false
    };

    CTFd.fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        body: JSON.stringify(params)
    }).then(function (response, reject) {
        return response.text();
    }).then(function (response, reject) {
        CTFd.lib.$("#oracle-details").html(response);
    });
};

newChallenge = function() {
    var challenge_id = CTFd.lib.$('#challenge-id-oracle').val();
    var url = "/plugins/oracle_challenges/" + challenge_id;

    var params = {
        'force_new': true
    };

    CTFd.fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        body: JSON.stringify(params)
    }).then(function (response) {
        return response.text();
    }).then(function (response) {
        CTFd.lib.$("#oracle-details").html(response);
    });
};


// fundWallet = function() {
//     var challenge_id = parseInt(CTFd.lib.$('#challenge-id').val());
//     var wallet_address = CTFd.lib.$('#wallet-address').val()
//     var url = "/plugins/oracle_challenges/" + challenge_id + "/fund";

//     var params = {
//         'wallet': wallet_address
//     };

//     CTFd.fetch(url, {
//         method: 'POST',
//         credentials: 'same-origin',
//         body: JSON.stringify(params)
//     }).then(function (response) {
//         return response.text();
//     }).then(function (response) {
//         const result_message = $("#result-message");
//         const result_notification = $("#result-notification");
// 	result_message.text(response);
//         result_notification.removeClass();
//         result_notification.addClass("alert alert-secondary alert-dismissable text-center");
//         result_notification.slideDown();
//         $("#fundwallet-key").prop("disabled", true);
//         setTimeout(function() {
//             $(".alert").slideUp();
//           }, 3000);
//     })
// };