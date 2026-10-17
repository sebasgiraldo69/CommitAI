import { getToken, request, setToken, setUser } from "./api.js";

if (getToken()) {
  window.location.href = "/";
}

const form = document.getElementById("register-form");
const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");
const confirmInput = document.getElementById("confirm-password");
const submitBtn = document.getElementById("submit-btn");
const messageEl = document.getElementById("auth-message");

function showError(msg) {
  messageEl.textContent = msg;
  messageEl.className = "message error";
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  messageEl.className = "message";
  messageEl.textContent = "";

  if (passwordInput.value !== confirmInput.value) {
    showError("Las contraseñas no coinciden.");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Creando cuenta…";

  try {
    const res = await request("/api/auth/register", {
      method: "POST",
      body: {
        email: emailInput.value.trim(),
        password: passwordInput.value,
      },
    });

    setToken(res.access_token);
    setUser(res.user);
    window.location.href = "/";
  } catch (err) {
    showError(err.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Crear mi cuenta";
  }
});
