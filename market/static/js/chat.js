// 채팅 화면 처리. 받은 메시지는 글자(textContent)로만 넣어서 태그가 실행되지 않게 한다
(function () {
  var box = document.getElementById("chat-messages");
  if (!box || typeof io === "undefined") return;

  var room = box.dataset.room;
  var form = document.getElementById("chat-form");
  var input = document.getElementById("chat-input");
  var socket = io();

  function appendMessage(username, content, isError) {
    var div = document.createElement("div");
    div.className = "chat-msg";
    if (isError) {
      div.style.color = "#c0392b";
      div.textContent = content;
    } else {
      var b = document.createElement("b");
      b.textContent = username;
      div.appendChild(b);
      div.appendChild(document.createTextNode(" " + content));
    }
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
  }

  socket.on("connect", function () {
    socket.emit("join", { room: room });
  });

  socket.on("new_message", function (data) {
    appendMessage(data.username, data.content, false);
  });

  socket.on("error_message", function (data) {
    appendMessage(null, data.msg, true);
  });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var content = input.value.trim();
    if (!content) return;
    socket.emit("send_message", { room: room, content: content });
    input.value = "";
  });

  box.scrollTop = box.scrollHeight;
})();
