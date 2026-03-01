package com.georgernstgraf.aitranscribe.util

import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File

/**
 * Test class for AudioChunker.
 * Tests audio file chunking functionality.
 */
class AudioChunkerTest {

    @get:Rule
    val temporaryFolder = TemporaryFolder()

    private lateinit var audioChunker: AudioChunker
    private lateinit var testAudioFile: File

    @Before
    fun setup() {
        audioChunker = AudioChunker(maxFileSizeMB = 25)
        
        testAudioFile = temporaryFolder.newFile("test_audio.mp3")
        testAudioFile.writeBytes(createFakeAudioData(1024 * 1024 * 10)) // 10 MB
    }

    @Test
    fun `chunkAudio returns single file for small audio`() = runTest {
        val chunks = audioChunker.chunkAudio(testAudioFile.absolutePath)
        
        assertEquals("Should return single chunk for small file", 1, chunks.size)
        assertEquals("Chunk path should match original", testAudioFile.absolutePath, chunks[0])
    }

    @Test
    fun `chunkAudio creates multiple chunks for large audio`() = runTest {
        val largeAudioFile = temporaryFolder.newFile("large_audio.mp3")
        largeAudioFile.writeBytes(createFakeAudioData(1024 * 1024 * 30)) // 30 MB

        val chunks = audioChunker.chunkAudio(largeAudioFile.absolutePath)

        assertTrue("Should create multiple chunks for large file", chunks.size > 1)
    }

    @Test
    fun `chunkAudio creates chunks under max size limit`() = runTest {
        val largeAudioFile = temporaryFolder.newFile("very_large_audio.mp3")
        largeAudioFile.writeBytes(createFakeAudioData(1024 * 1024 * 50)) // 50 MB

        val chunks = audioChunker.chunkAudio(largeAudioFile.absolutePath)

        for (chunk in chunks) {
            val chunkFile = File(chunk)
            val sizeMB = chunkFile.length() / (1024.0 * 1024.0)
            assertTrue("Each chunk should be under max size limit", sizeMB <= 25.0)
        }
    }

    @Test
    fun `chunkAudio uses original path for single chunk`() = runTest {
        val chunks = audioChunker.chunkAudio(testAudioFile.absolutePath)

        assertEquals("Should use original file path", testAudioFile.absolutePath, chunks[0])
    }

    @Test
    fun `chunkAudio creates named chunks`() = runTest {
        val largeAudioFile = temporaryFolder.newFile("test_large_audio.mp3")
        largeAudioFile.writeBytes(createFakeAudioData(1024 * 1024 * 30))

        val chunks = audioChunker.chunkAudio(largeAudioFile.absolutePath)

        for ((index, chunk) in chunks.withIndex()) {
            val chunkFile = File(chunk)
            assertTrue("Chunk file should exist", chunkFile.exists())
            assertTrue(
                "Chunk should have naming pattern",
                chunkFile.name.contains("_chunk$index")
            )
        }
    }

    @Test
    fun `chunkAudio handles 10 minute segments`() = runTest {
        val chunks = audioChunker.chunkAudio(testAudioFile.absolutePath)

        for (chunk in chunks) {
            val chunkFile = File(chunk)
            assertTrue("Chunk file should be mp3 format", chunkFile.extension == "mp3")
        }
    }

    @Test
    fun `getAudioDuration returns duration in seconds`() = runTest {
        val duration = audioChunker.getAudioDuration(testAudioFile.absolutePath)

        assertTrue("Duration should be positive", duration > 0)
    }

    @Test(expected = IllegalArgumentException::class)
    fun `chunkAudio throws exception for non-existent file`() = runTest {
        audioChunker.chunkAudio("/non/existent/file.mp3")
    }

    @Test
    fun `chunkAudio respects custom max size`() = runTest {
        val customChunker = AudioChunker(maxFileSizeMB = 10)
        val largeAudioFile = temporaryFolder.newFile("custom_test.mp3")
        largeAudioFile.writeBytes(createFakeAudioData(1024 * 1024 * 25))

        val chunks = customChunker.chunkAudio(largeAudioFile.absolutePath)

        assertTrue("Should create multiple chunks with custom max size", chunks.size > 1)

        for (chunk in chunks) {
            val chunkFile = File(chunk)
            val sizeMB = chunkFile.length() / (1024.0 * 1024.0)
            assertTrue("Each chunk should be under custom max size", sizeMB <= 10.0)
        }
    }

    private fun createFakeAudioData(size: Int): ByteArray {
        return ByteArray(size) { (it % 256).toByte() }
    }
}