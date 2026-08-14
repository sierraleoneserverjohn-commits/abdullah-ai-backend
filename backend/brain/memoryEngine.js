const fs = require("fs");
const path = require("path");

const BRAIN_DIR = __dirname;

const brain = JSON.parse(
  fs.readFileSync(path.join(BRAIN_DIR, "brain.json"), "utf8")
);

const messages = JSON.parse(
  fs.readFileSync(path.join(BRAIN_DIR, "chat_archive.json"), "utf8")
);

/**
 * Simple text normalization
 */
function normalize(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Break a message into searchable words.
 */
function words(text) {
  return new Set(
    normalize(text)
      .split(" ")
      .filter(word => word.length > 2)
  );
}

/**
 * Calculate how relevant a stored message is
 * to Sana's current message.
 */
function relevance(query, storedMessage) {
  const queryWords = words(query);
  const messageWords = words(storedMessage);

  if (!queryWords.size || !messageWords.size) return 0;

  let matches = 0;

  for (const word of queryWords) {
    if (messageWords.has(word)) {
      matches++;
    }
  }

  return matches / queryWords.size;
}

/**
 * Search Abdullah's complete WhatsApp history.
 */
function searchChat(query, limit = 8) {
  const results = [];

  for (const message of messages) {
    const score = relevance(query, message.message);

    if (score > 0) {
      results.push({
        score,
        id: message.id,
        date: message.date,
        time: message.time,
        sender: message.sender,
        message: message.message
      });
    }
  }

  return results
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}

/**
 * Search extracted memory candidates.
 */
function searchMemory(query, limit = 5) {
  const file = path.join(BRAIN_DIR, "memory_candidates.json");

  if (!fs.existsSync(file)) return [];

  const memories = JSON.parse(fs.readFileSync(file, "utf8"));

  return memories
    .map(memory => ({
      ...memory,
      score: relevance(query, memory.message)
    }))
    .filter(memory => memory.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}

/**
 * Build the context that will be sent to the AI model.
 */
function buildContext(query) {
  const chatResults = searchChat(query, 8);
  const memoryResults = searchMemory(query, 5);

  return {
    profile: brain.person,
    relationship: brain.relationship,

    memories: memoryResults.map(memory => ({
      date: memory.date,
      sender: memory.sender,
      message: memory.message,
      categories: memory.candidate_categories
    })),

    conversations: chatResults.map(message => ({
      date: message.date,
      sender: message.sender,
      message: message.message
    }))
  };
}

/**
 * Main function Abdullah's backend will call.
 */
function remember(query) {
  return buildContext(query);
}

module.exports = {
  searchChat,
  searchMemory,
  buildContext,
  remember
};
