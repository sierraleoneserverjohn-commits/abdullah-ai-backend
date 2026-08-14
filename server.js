const express = require("express");
const { remember } = require("./brain/memoryEngine");

const app = express();

app.use(express.json());

app.post("/chat", async (req, res) => {
  try {
    const userMessage = req.body.message;

    if (!userMessage) {
      return res.status(400).json({
        error: "Message is required"
      });
    }

    // 🧠 Search Abdullah's brain
    const memory = remember(userMessage);

    console.log("🧠 Abdullah memory:", memory);

    // Your AI API goes here
    // Example:
    //
    // const response = await callGroq(userMessage, memory);

    res.json({
      message: userMessage,
      memory
    });

  } catch (error) {
    console.error(error);

    res.status(500).json({
      error: "Abdullah brain error"
    });
  }
});

app.listen(3000, () => {
  console.log("🧠 Abdullah Brain running on port 3000");
});
